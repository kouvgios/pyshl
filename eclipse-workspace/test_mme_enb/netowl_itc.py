#!/usr/bin/env python3

# ##
# itcLib provides basic communication with netowl tools using libnetowlitc.so
# when running standalone this can be used as simple cli client for itcLib testing purposes
# ##

from ctypes import Structure
from ctypes import POINTER
from ctypes import CFUNCTYPE
from ctypes import c_uint8
from ctypes import c_uint16
from ctypes import c_uint64
from ctypes import c_int
from ctypes import c_ushort
from ctypes import c_void_p
from ctypes import c_char_p
from ctypes import cast
from ctypes import cdll
# from time import sleep
import select
# if not "EPOLLRDHUP" in dir(select):
#    select.EPOLLRDHUP = 0x2000
import ipaddress

import queue
import threading

import os
import sys
import fcntl
from datetime import datetime
import struct
import json
# import pprint

import logging
import traceback

print("setting logger")
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.ERROR)

itcLib = None

# help for itcLib cli thread commands that is used to test itcLib


def printHelp():
    print(
        """netowl_itc.py [--sim <simulator-name>] [--simInstId <number>] [--ip simIpAddress] [--port simItcPort] [--instId <number>] [--libPath <pathToItcLibrary>]
    NetOwl python api. As standalone can be used as simple client
    - To send command to sim just write command and press enter (will ask worker thread to send command to sim)
    - in sim must be started itc service e.g.: set cs server 12 tcp 135.243.195.183 8000
    - if json is not set by default start json in sim-mme-enb enter set json-file stdout
    local commands:
        ? - help
        q - quit
        #ii - ipdb
        #i - pdb
        #t - trepan3k (gdb like debugger)
        #version - print version
        #s1 - short stats
        #stats - call itc_print_stats
        #send <num> - send num messages
        #something else - send "something else" to sim from test thread
        j - toggle parse output of cmd to json
        v - toggle verbose receive mode
        r - print raw answers (reenable print after s,l,t commands)
        s - printStats
        s NUMBER - test thread ask worker NUMBER times using tuple to send commands
        l NUMBER - test thread ask worker
         NUMBER times using lambda to send commands
        t NUMBER - test thread to send NUMBER commands directly
        e - toggle empty line behavior
        '' - empty line calls printStats and pyapi_print_stats (must be enabled by e)\n""")


###################################################################
# structures used in cli itc messaging

# /* This structure is included in every message, but */
# /* it is read only (accessible only on the receive side) */
# typedef struct {
#        uint8_t msgType; /* eNetOwlCsMsgType */
#        uint8_t version;
#        uint8_t sender; /* eNetOwlCsObjects */
#        uint8_t senderInstId;
# } tNcsCommonMsgHeader;


class tNcsCommonMsgHeader(Structure):
    _fields_ = [
        ("msgType", c_uint8),
        ("version", c_uint8),
        ("sender", c_uint8),
        ("senderInstId", c_uint8)
    ]


# /* structure received by itc_handler callback function */
# typedef struct ncsMsg_s
# {
#        tNcsCommonMsgHeader ncsHdr;
#        uint8_t             data[ITC_BUF_SIZE];
# } ncsMsg_t;

class ncsMsg_t(Structure):
    _fields_ = [
        ("ncsHdr", tNcsCommonMsgHeader),
        ("data", c_uint8 * 2048)
    ]


# /* first 4 data bytes used to specify next content of cli message */
# typedef struct
# {
#        uint8_t msgType;
#        uint8_t msgOptions;
#        uint16_t seqNum;
# } tItcCliMsgHeader;

class tItcCliMsgHeader(Structure):
    _fields_ = [
        ("msgType", c_uint8),
        ("msgOptions", c_uint8),
        ("seqNum", c_uint16),
    ]


###################################################################
# functions to cooperate with netowl library

# Callback func to itc_set_handle
# this function is called from receiver thread when it has complete itc message
#
# typedef int ( *itc_handler )( ncsMsg_t*, uint16_t, void* ); /* handler implemented in sim (no xdr) */

@CFUNCTYPE(c_int, POINTER(ncsMsg_t), c_ushort, c_void_p)
def py_itc_handler(msg, msgLen, userPtr):
    # logger.info("called py_itc_handler - cli message received")
    # logger.info( msg.contents.ncsHdr.msgType )
    # logger.info( msg.contents.ncsHdr.version )
    # logger.info( msg.contents.ncsHdr.sender )
    # logger.info( msg.contents.ncsHdr.senderInstId )
    # logger.info( bytes(msg.contents.data[0:msgLen - 4]).decode("utf-8") )
    # logger.info( msgLen )
    cliHdr = cast(msg.contents.data, POINTER(tItcCliMsgHeader))
    cliMsgData = bytes(msg.contents.data[4:msgLen - 4]).decode("utf-8")
    if ItcThread.sndRcvVerbose:
        logger.info("cliHdr: msgType: {}, msgOpt: {}, seqNum: {}, msgLen: {}, data: {}".format(
            cliHdr.contents.msgType, cliHdr.contents.msgOptions, cliHdr.contents.seqNum, msgLen, cliMsgData))
        if ItcThread.tryJson and (msgLen > 8) and (cliHdr.contents.msgOptions & 0x2):
            # import pdb; pdb.set_trace()
            try:
                jsonData = json.loads(cliMsgData)
                # pprint.pprint( answer )
                logger.info("json answer: {}".format(jsonData))
            except ValueError as e:
                logger.info("failed to transform to json: >>>{}<<< {}".format(cliMsgData, e))
        else:
            logger.info("raw answer: {}".format(cliMsgData))
            # logger.info( str ( bytes ( msg.contents.data[4:msgLen-4] ) ) )
            # import pdb; pdb.set_trace()
    ItcThread.seqNumR = cliHdr.contents.seqNum
    # print ("userPtr: {}".format(userPtr))
    recvCallback = ItcThread.recvCallbacks[userPtr]
    # print ("recvCallback from userPtr: {}".format(recvCallback))
    # import pdb; pdb.set_trace()
    if callable(recvCallback):
        recvCallback(cliHdr.contents, cliMsgData)
    ItcThread.counterRecv = ItcThread.counterRecv + 1
    return 0


# delete last newline characters
def chomp(x):
    if x.endswith("\r\n"):
        return x[:-2]
    if x.endswith("\n"):
        return x[:-1]
    return x


def doCall(fd, event, fn, arg):
    fn(fd, event, arg)


class ItcThread (threading.Thread):

    fdHandlers = {}
    recvCallbacks = {}
    sndRcvVerbose = False
    counterSend = 0
    counterRecv = 0
    seqNumR = 0
    seqNumS = 0
    tryJson = False

    def __init__(self, threadID, name, itcLib):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.jobsQ = queue.Queue()
        self.netowl = itcLib.netowl
        self.myInstId = itcLib.myInstId
        self.eventFd = self.netowl.pyapi_get_eventfd()
        self.epoll = select.epoll()
        self.setFdHandler(self.eventFd, self.handleEventFd, None)
        self.eventFdEvents = 0
        self.getfd_fn = self.netowl.itc_get_fd
        self.getfd_fn.restype = c_int

    def run(self):
        logger.info("thread started")
        self.pollEnabled = True
        # as myInstId is thred specific it must be set in this thread to enable receive
        self.netowl.netOwlCsSetMyInstId(c_int(self.myInstId))
        self.doPool()
        logger.info("thread exit")

    # function called when there are data on any itc file descriptor
    def handleItcFd(self, fd, event, arg):
        # logger.info("got new msg")
        context = c_void_p(arg)
        self.netowl.itc_cln_process_tcp_client(context)
        netOwlFd = self.getfd_fn(context)
        if (netOwlFd == -1) and (fd in ItcThread.recvCallbacks):
            # if event & select.EPOLLRDHUP:
            recvCallback = ItcThread.recvCallbacks[fd]
            if callable(recvCallback):
                recvCallback(tItcCliMsgHeader(msgType=255), "Disconnected from itc peer from socket {}".format(fd))

    # function called when there are data on task pipe file descriptor
    def handleEventFd(self, fd, event, arg):
        data = os.read(self.eventFd, 8)
        num = struct.unpack('@Q', data)[0]
        self.eventFdEvents += num
        if ItcThread.sndRcvVerbose:
            logger.info("handleEventFd job num: {}".format(num))
        self.handleJobQueue(100)

    # process up to num jobs from jobsQ
    def handleJobQueue(self, num):
        while num > 0 and not self.jobsQ.empty():
            job = self.jobsQ.get_nowait()
            num -= 1
            self.eventFdEvents -= 1
            if callable(job):
                job()
            elif isinstance(job, tuple) and len(job) > 0 and callable(job[0]):
                if len(job) == 2:
                    if isinstance(job[1], tuple):
                        job[0](*job[1])
                    else:
                        job[0](job[1])
                elif len(job) == 1:
                    job[0]()
                else:
                    logger.info("handleEventFd: too much arguments: {}, job: {}".format(len(job), job))
            else:
                logger.info("handleEventFd: received non callable job: {}".format(job))

    # puts job to queue and signal to eventfd to wake up worker thread
    def putJobAndSignal(self, job):
        data1 = c_uint64(1)  # b'\x00\x00\x00\x00\x00\x00\x00\x01'
        self.jobsQ.put(job)
        # signal eventfd
        os.write(self.eventFd, data1)

    def printStats(self):
        print(
            "Tx: %10d, Rx: %10d, seqNum %5d %5d, t: " %
            (ItcThread.counterSend,
             ItcThread.counterRecv,
             ItcThread.seqNumS,
             ItcThread.seqNumR),
            datetime.now())

    # function sending itc messages
    def sendMsg(self, context, data, seqNum=-1, msgType=0, msgOptions=0):
        if seqNum == -1:
            seqNum = (ItcThread.seqNumS + 1) & 0xffff
        ItcThread.seqNumS = seqNum

        # data = chomp(data)
        buf = bytes(4) + bytes(data, 'utf-8')
        msgp = c_char_p(buf)
        cliHdr = cast(msgp, POINTER(tItcCliMsgHeader))
        cliHdr.contents.msgType = msgType
        cliHdr.contents.msgOptions = msgOptions
        cliHdr.contents.seqNum = seqNum

        if ItcThread.sndRcvVerbose:
            logger.info(
                "sendMsg sending: context: {}, msgType: {}, msgOpt: {}, seqNum: {}, data: {}".format(
                    context, msgType, msgOptions, seqNum, data))

        result = self.netowl.itc_cln_send(c_void_p(context), 7, msgp, c_int(len(buf)))
        if (result != len(buf)):
            fd = self.netowl.itcGetUsrPtr(c_void_p(context))
            if fd in ItcThread.recvCallbacks:
                recvCallback = ItcThread.recvCallbacks[fd]
                if callable(recvCallback):
                    recvCallback(tItcCliMsgHeader(msgType=255), "Write error itc peer from socket {}".format(fd))

        ItcThread.counterSend = ItcThread.counterSend + 1

    # poll and handle events in loop
    def doPool(self):
        try:
            while self.pollEnabled:
                if self.eventFdEvents > 0:
                    self.handleJobQueue(10)
                events = self.epoll.poll(1)
                for fileno, event in events:
                    if fileno in self.fdHandlers:
                        handler = self.fdHandlers[fileno]

                        if(handler):
                            doCall(fileno, event, *handler)

        finally:
            # if fdStdin in self.fdHandlers :
            #    self.epoll.unregister(fdStdin)
            self.epoll.close()

    def doPool1(self):
        events = self.epoll.poll(1)
        for fileno, event in events:
            if fileno in self.fdHandlers:
                handler = self.fdHandlers[fileno]

                if(handler):
                    doCall(fileno, event, *handler)

    def connectToServer(self, sim):

        instId = sim['instId']
        port = sim['port']
        srvIp = int(ipaddress.IPv4Address(sim['ip']))
        logger.info("srvIp: {}".format(srvIp))
        srvNcso = self.netowl.netOwlCsNameToObject(sim['name'].encode('ascii'))
        logger.info("srvNcso: {}".format(srvNcso))

        # ITC_Context* itcConnectToServer(int myInstId, eNetOwlCsTypes type,
        # tNcsAddr addr, uint16_t port, eNetOwlCsObjects server, int instId,
        # uint32_t bufSize, int autoInst)
        itcConnectToServer = self.netowl.itcConnectToServer
        itcConnectToServer.restype = c_void_p
        context = itcConnectToServer(
            c_int(
                self.myInstId),
            c_int(1),
            c_int(srvIp),
            c_int(port),
            srvNcso,
            c_int(instId),
            c_int(2048),
            c_int(0))
        logger.info("Context: {}".format(context))

        return context

    def setFdHandler(self, fd, fn, context):
        # self.epoll.register(fd, select.EPOLLIN | select.EPOLLRDHUP)
        self.epoll.register(fd, select.EPOLLIN)
        self.fdHandlers[fd] = (fn, context)

    def setFdRecvCallback(self, fd, recvCallback):
        self.recvCallbacks[fd] = recvCallback

    def clearFd(self, fd, context):
        self.epoll.unregister(fd)
        del(self.fdHandlers[fd])
        del(self.recvCallbacks[fd])


def getItcLib(*args, autoInit=True, **kwargs):
    global itcLib
    if itcLib is None and autoInit:
        itcLib = ItcLib(*args, **kwargs)
    return itcLib


class ItcLib ():
    # initialize itc modul
    def __init__(self, myInstId=1, itcLibraryPath="/opt/netowl/lib"):
        if itcLib is not None:
            raise ValueError("itcLib initialized already")
        self.itcLibrary = itcLibraryPath + "/libnetowlitc.so"
        logger.info("itcLibrary: {}".format(self.itcLibrary))

        self.netowl = cdll.LoadLibrary(self.itcLibrary)
        print("opened netowl-itc library version: {}, path: {}".format(self.getVersion(), self.itcLibrary))

        self.initCs(myInstId)
        self.setMsgHandler()
        self.worker = ItcThread(1, "epolThread", self)
        self.worker.start()

    # one time intialization of python api library
    def initCs(self, myInstId):
        self.myInstId = myInstId
        self.netowl.pyapi_init("pygash".encode('ascii'), c_int(myInstId))

    def setMsgHandler(self):
        self.netowl.itc_set_cli_handler(py_itc_handler)

    def getAndSetFd(self, context, recvCallback):
        netOwlFd = self.worker.getfd_fn(c_void_p(context))
        fl = fcntl.fcntl(netOwlFd, fcntl.F_GETFL)
        fcntl.fcntl(netOwlFd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        logger.info("getFd: {}".format(netOwlFd))

        self.worker.setFdHandler(netOwlFd, self.worker.handleItcFd, context)
        self.worker.setFdRecvCallback(netOwlFd, recvCallback)
        self.netowl.itcSetUsrPtr(c_void_p(context), cast(netOwlFd, c_void_p))

    def closeFd(self, context):
        # netOwlFd = self.worker.getfd_fn(c_void_p(context))
        netOwlFd = self.netowl.itcGetUsrPtr(c_void_p(context))
        self.netowl.itc_destroy(c_void_p(context))
        self.worker.clearFd(netOwlFd, context)

    def sendMsg(self, context, data, seqNum=-1, msgType=0, msgOptions=0):
        if ItcThread.sndRcvVerbose:
            logger.info(
                "sendMsg enqueue: context: {}, msgType: {}, msgOpt: {}, seqNum: {}, data: {}".format(
                    context, msgType, msgOptions, seqNum, data))
        self.sendJob(lambda: self.worker.sendMsg(context, data, seqNum, msgType, msgOptions))

    def sendJob(self, fn, arg=None):
        if arg is None:
            job = fn
        else:
            job = (fn, arg)
        self.worker.putJobAndSignal(job)

    def close(self):
        global itcLib
        self.worker.pollEnabled = False
        self.worker.join()
        itcLib = None

    def getVersion(self):
        self.netowl.pyapi_get_version.restype = c_char_p
        return self.netowl.pyapi_get_version().decode("utf-8")


###########################################
###########################################
####
# Helper functions to test itcLib
####
###########################################
###########################################

# wait for jobs at mainQ
def testThread():
    logger.info("Started test thread")
    try:
        while pollMainEnabled:
            event = mainQ.get()
            event()

    except Exception as e:
        logger.info(e)
    logger.info("finished test thread")


# called from itcLib when received message
def handleMsgRawPrint(cliHdr, cliMsgData):
    # logger.debug("received itc msg: {}, {}".format(cliHdr, cliMsgData))
    if rawPrint:
        print(cliMsgData)


# loop handleStdin - creates blocking stdin handling
# this is alternative to stdin registration to epoll
def cliLoop(fdStdin):
    logger.info("cliLoop started")
    while(pollMainEnabled):
        handleStdIn(fdStdin, None)
    logger.info("cliLoop finished")


# read one time from stdin and process
def handleStdIn(fdStdin, arg):
    global emptyLineStats
    global rawPrint
    global pollMainEnabled

    data = ""
    line1 = os.read(fdStdin, 64)
    data += line1.decode("utf-8")
    data = chomp(data)

    if data == "?":
        printHelp()
    elif data == "q":
        pollMainEnabled = False
        mainQ.put(lambda: itcLib.netowl.pyapi_print_stats())
    elif data == "s":
        itcLib.worker.printStats()
    elif data == "":
        if emptyLineStats:
            itcLib.worker.printStats()
            itcLib.netowl.pyapi_print_stats()
        else:
            itcLib.sendMsg(context, "")
    elif data.startswith("s "):
        mainQ.put(lambda: timedSendTuple(context, int(data[2:])))
    elif data.startswith("t "):
        mainQ.put(lambda: timedSendLocal(context, int(data[2:])))
    elif data.startswith("l "):
        mainQ.put(lambda: timedSendLambda(context, int(data[2:])))
    elif data == "j":
        ItcThread.tryJson = not ItcThread.tryJson
        print(" ItcThread.tryJson: " + str(ItcThread.tryJson))
    elif data == "v":
        ItcThread.sndRcvVerbose = not ItcThread.sndRcvVerbose
        print(" ItcThread.sndRcvVerbose: " + str(ItcThread.sndRcvVerbose))
    elif data == "e":
        emptyLineStats = not emptyLineStats
        print(" emptyLineStats: " + str(emptyLineStats))
    elif data == "r":
        rawPrint = not rawPrint
        print(" rawPrint: " + str(rawPrint))
    elif data.startswith("#"):
        cmd = data[1:]
        if cmd == "stats":
            itcLib.netowl.pyapi_print_stats()
            # netowl.itc_print_stats( cStdOut )
        elif cmd == "version":
            print("library version: " + itcLib.netowl.pyapi_get_version())
        elif cmd == "t":
            try:
                print("trepan debugger")
                # from trepan.api import debug
                # debug()
            except Exception as e:
                print(e)

        elif cmd == "ii":
            print("ipdb debugger")
            # import ipdb
            # ipdb.set_trace()
        elif cmd == "i":
            import pdb
            pdb.set_trace()
        elif cmd == "s1":
            itcLib.worker.printStats()
        elif "send" in cmd:
            timedSendLocal(context, int(cmd[5:]))
        else:
            mainQ.put(lambda: itcLib.worker.sendMsg(context, cmd))
    else:
        itcLib.sendMsg(context, data)
        # mainQ.put(lambda: itcLib.sendJob( lambda: itcLib.worker.sendMsg( context, data ) ) )


# send in loop from current thread
def timedSendLocal(context, loops):
    global rawPrint
    if loops > 10:
        ItcThread.sndRcvVerbose = False
        rawPrint = False
    start_time = datetime.now()

    for x in range(0, loops):
        itcLib.worker.sendMsg(context, "show version")

    time_elapsed = datetime.now() - start_time
    logger.info('Time elapsed (hh:mm:ss.ms) {}'.format(time_elapsed))


# ask worker to send message via lambda in loop
def timedSendLambda(context, loops):
    global rawPrint
    if loops > 10:
        ItcThread.sndRcvVerbose = False
        rawPrint = False
    start_time = datetime.now()

    for x in range(0, loops):
        itcLib.sendJob(lambda: itcLib.worker.sendMsg(context, "show version"))

    time_elapsed = datetime.now() - start_time
    logger.info('Time elapsed (hh:mm:ss.ms) {}'.format(time_elapsed))


# ask worker to send message via tuple in loop
def timedSendTuple(context, loops):
    global rawPrint
    if loops > 10:
        ItcThread.sndRcvVerbose = False
        rawPrint = False
    start_time = datetime.now()

    for x in range(0, loops):
        itcLib.sendJob(itcLib.worker.sendMsg, (context, "show version"))

    time_elapsed = datetime.now() - start_time
    logger.info('Time elapsed (hh:mm:ss.ms) {}'.format(time_elapsed))


###########################################
def error(s):
        print("-E-" * 15)
        print("ERROR:", s)
        print("-E-" * 15)
        print("ARGUMENTS: " + ", ".join(sys.argv))
        printHelp()
        exit()


# raised form getNextParam
class ParamError(Exception):
    def __init__(self, arg):
        self.args = arg


# gets next system argument
def getNextParam():
    if (getNextParam.p > (len(sys.argv) - 1)):
        raise ParamError("no more params")
    param = sys.argv[getNextParam.p]
    getNextParam.p += 1
    return param


# test function just logging that it was called
# used to test lambdas in queues with multiple threads
def f2(s1, s2):
    logger.info("s1: {}, s2: {}".format(s1, s2))


# when running as standalone trying to connect to ip and port through netolwlibrary
if __name__ == "__main__":
    sh = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(threadName)15s %(name)s '
                                  'ln: %(lineno)d - %(levelname)s - %(message)s')
    sh.setFormatter(formatter)
    logging.root.addHandler(sh)
    logging.root.setLevel(logging.DEBUG)

    logger.setLevel(logging.NOTSET)
    print("logger.getEffectiveLevel: ", logger.getEffectiveLevel())

    logger.info("starting in cli client mode")

    myInstId = 2
    sim = {"name": "sim-mme-enb", "ip": "127.0.0.1", "port": 8000, "instId": 1}
    
    myInstId = 1
    sim = {"name": "sim-mme-enb", "ip": "127.0.0.1", "port": 8000, "instId": 1}
    itcLibraryPath = "/opt/netowl/lib/"
    pollMainEnabled = True
    # ItcThread.tryJson = True
    # ItcThread.sndRcvVerbose = True
    emptyLineStats = False
    rawPrint = True
    
    mainQ = queue.Queue()
    import pdb; pdb.set_trace()
    if (len(sys.argv) < 0):
        printHelp()
        exit()

    getNextParam.p = 1
    try:
        while (True):
            try:
                param = getNextParam()
            except ParamError:
                break
            if (param == "--help"):
                printHelp()
                exit()
            elif (param == "--sim"):
                sim['name'] = getNextParam()
            elif (param == "--simInstId"):
                sim['instId'] = int(getNextParam())
            elif (param == "--ip"):
                sim['ip'] = getNextParam()
            elif (param == "--port"):
                sim['port'] = int(getNextParam())
            elif (param == "--instId"):
                myInstId = int(getNextParam())
            elif (param == "--libPath"):
                itcLibraryPath = getNextParam()
            else:
                logger.info("Invalid argument: ", param)
    except ValueError:
        error("Invalid value specified after " + sys.argv[getNextParam.p - 2])

    logger.info("myInstId: {}".format(myInstId))
    logger.info("sim: {}".format(sim))

    try:
        itcLib = ItcLib(myInstId, itcLibraryPath)

        fdStdin = sys.stdin.fileno()
        # if we want to handle stdin on worker thread scope
        # fl = fcntl.fcntl(fdStdin, fcntl.F_GETFL)
        # fcntl.fcntl(fdStdin, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        # itcLib.worker.setFdHandler( fdStdin, handleStdIn, None)

        # # if we want to start separate thread for cliLoop
        # start new thread for test instead of setFdHandler
        # t = threading.Thread(target=cliLoop)

        t = threading.Thread(target=testThread)
        t.start()

        context = itcLib.worker.connectToServer(sim)
        if not context:
            logger.info("Cannot connect to:  {}".format(sim))
            raise ValueError("no more params")
        # itcLib.getAndSetFd(context, sim)
        itcLib.getAndSetFd(context, handleMsgRawPrint)

        # sleep( 2 )
        # itcLib.sendJob(lambda: f2("ahoj", "pokus"))
        # itcLib.sendJob(f2, (context, "pokus"))
        logger.info("going to call enqueue sendMsg from this thread")
        itcLib.sendMsg(context, "show stats itc")

        cliLoop(fdStdin)

    except Exception as e:
        logger.info(e)
        traceback.print_tb(e.__traceback__)
        pollMainEnabled = False
        mainQ.put(lambda: itcLib.netowl.pyapi_print_stats())

    itcLib.close()
    # itcLib.sendJob(lambda: f2("ahoj", "pokus"))
    t.join()
