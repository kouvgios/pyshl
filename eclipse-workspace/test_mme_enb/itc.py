import queue
import threading
import logging
from collections import namedtuple
import time
# import netowl_itc
from netowl_itc import getItcLib
import json
# import pprint

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.ERROR)
# logger.setLevel(logging.DEBUG)


# Task = namedtuple("Task", ("id", "name", "callback"))
Result = namedtuple("Result", ("data", "estr", "rtc"))
MsgResult = namedtuple("MsgResult", ("msgType", "msgOptions", "seqNum", "data"))
eItcCliMsgType_nt = namedtuple("eItcCliMsgType", (
    "itcCliReq",
    "itcCliRes",
    "itcCliResErr",
    "itcCliResFrag"))
eItcCliMsgType = eItcCliMsgType_nt(*list(range(4)))

itcLib = None
simList = []


class Timeout(Exception):
    pass


# TODO: handle endTime i.e. acmd timeout
class Task(object):
    """docstring for Task"""

    def __init__(self, cmd, callback, sim, timeout):
        super(Task, self).__init__()
        self._task_state = "PENDING"
        self.__callback = callback
        self.__id = hex(id(self))
        self.__cmd = cmd
        self._endTime = time.time() + timeout if timeout else None
        self._result = None
        self._sim = sim

    def __str__(self):
        return str(vars(self))

    def done(self):
        return "DONE" in self._task_state

    def __set_state(self, state):
        self._task_state = state

    @property
    def callback(self):
        return(self.__callback)

    @property
    def id(self):
        return(self.__id)

    @property
    def state(self):
        return(self._task_state)

    @property
    def cmd(self):
        return(self.__cmd)

    @property
    def result(self):
        return self._result


def getVersion():
    theItcLib = getItcLib()
    return theItcLib.getVersion()


def close():
    while len(simList) > 0:
        sim = simList[-1]
        logger.debug("close:sim: {}, simlist: {}".format(sim, simList))
        sim.close()
    itcLib1 = getItcLib(autoInit=False)
    if itcLib1 is not None:
        logger.debug("close:itcLib1 {}".format(itcLib1))
        itcLib1.close()


class Itc(object):

    def __init__(self, sim, defaultTimeout=30):
        global itcLib
        logger.info("Itc: connecting to {}".format(sim))
#        logger.info("Itc: connecting to {}".format(sim2))
        itcLib = getItcLib()
        self.simItcContext = itcLib.worker.connectToServer(sim)
#        self.sim2ItcContext = itcLib.worker.connectToServer(sim2)
        logger.info("Ict: {}".format(self.simItcContext))
        if not self.simItcContext:
            logger.error("Cannot connect to: {}".format(sim))
            raise ValueError("Cannot connect to: " + str(sim))
        itcLib.getAndSetFd(self.simItcContext, lambda cliHdr, cliMsgData: self.__handleMsg(cliHdr, cliMsgData))
        #import pdb; pdb.set_trace()
        self.sim = sim
#        self.sim2 = sim2
        # self.exceptionOnCmdError = False
        self.exceptionOnCmdError = True
        self._defaultTimeout = defaultTimeout
        self.__inq = queue.Queue()
        self.__outq = queue.Queue()
        self.__workQueue = queue.Queue()
        self.seqNumS = 0
        self.seqNumR = 0
        self.seqWindow = 1000
        self._e_task_done = threading.Semaphore(0)
        # self._e_task_done = threading.Event()
        self.__sent = {}
        self.pending = []
        self.__main_loop = self.__start()
        simList.append(self)

    # called from itcLib when received message
    def __handleMsg(self, cliHdr, cliMsgData):
        # logger.debug("received itc msg: {}, {}".format(cliHdr, cliMsgData))
        self.__workQueue.put(MsgResult(cliHdr.msgType, cliHdr.msgOptions, cliHdr.seqNum, cliMsgData))
        # self.res1.append(MsgResult(cliHdr.msgType, cliHdr.msgOptions, cliHdr.seqNum, cliMsgData))

    def __start(self):
        t = threading.Thread(target=self.__main_loop)
        t.start()
        return(t)

    def __process_task(self, task, e_task_done):

        # import pdb; pdb.set_trace()
        try:
            result = self.__proces_cmds(task.cmd)
            task._task_state = "DONE"
            task._result = (result)
            self.pending.remove(task)
            logger.debug("Setting task done")

        except Exception as e:
            logger.error("signalling other thread process_task catched Exception {}".format(e))
            task._task_state = "DONE"
            if task.callback is None:
                # e_task_done.set()
                e_task_done.release()
            raise e

        if task.callback is not None:
            task.callback(task)
        else:
            logger.debug("signalling other thread process_task finished {}".format(task))
            # e_task_done.set()
            e_task_done.release()

    def __sendCommand(self, command, cmdsSent):
        # logger.debug("Sending command '{}'".format(command))
        seqNum = (self.seqNumS + 1) & 0xffff
        msgType = eItcCliMsgType.itcCliReq
        msgOptions = 0
        if cmdsSent > 0:
            msgOptions = 1
        else:
            self.firstSeqNum = seqNum

        itcLib.sendMsg(self.simItcContext, command, seqNum, msgType, msgOptions)
        # 1# send directly from sim thread is 2x faster but need some rework in itcLib
        # 1# itcLib.worker.sendMsg(self.simItcContext, command, seqNum, msgType, msgOptions)
        # 1# self.res1.append(MsgResult(1, 0, seqNum, '{"ProgramVersion": "4.220"}')) # loop test without sending
        self.__sent[seqNum] = command
        self.seqNumS = seqNum

    def __waitMessage(self, num):
        resIdx = len(self.data)
        expectedIdx = resIdx + num
        while resIdx < expectedIdx:
            result = self.__workQueue.get()
            if result.msgType == 255:
                print("result: {}".format(result.data))
                self.errstr = result.data
                raise ValueError("ERROR itc peer: ", self.sim, result.data)
            if resIdx == 0 and result.seqNum != self.firstSeqNum:
                continue
            self.res1.append(result)
            # 1# while len(self.res1) <= resIdx:
            # 1#    itcLib.worker.doPool1()
            # 1#    # first command skip unprocessed results up to propper sequence number
            # 1#    if resIdx == 0 and len(self.res1) > 0 and self.res1[0].seqNum != self.firstSeqNum:
            # 1#        del(self.res1[0])

            resIdx += self.__process_res1(result)

    def __process_res1(self, res1):
        if res1 == -1:
            raise Timeout()
        cliMsgData = self.resultBufer + res1.data
        # big slow down even if debug is turned off
        # logger.debug("recv from workQueue: seqNumS: {}, res1: {}".format(self.seqNumS, res1))
        try:
            command = self.__sent[res1.seqNum]

            if res1.msgType == eItcCliMsgType.itcCliResErr:
                raise ValueError("sim failed to execute", command, cliMsgData)
            elif res1.msgType == eItcCliMsgType.itcCliRes:
                if len(cliMsgData) > 0:
                    try:
                        jsonData = json.loads(cliMsgData)
                        self.data.append(jsonData)
                        # pprint.pprint( answer )
                        # big slow down even if debug is turned off
                        # logger.debug( "json answer: {}".format(jsonData))
                    except ValueError as e:
                        if (res1.msgOptions & 0x02):
                            # 0x02 option means that valid json shoul be present
                            e.args = (e.args, "failed to transform to json: >>>{}<<< {}".format(cliMsgData, e))
                            raise e
                        else:
                            self.data.append(cliMsgData)
                else:
                    self.data.append(None)
            elif res1.msgType == eItcCliMsgType.itcCliResFrag:
                self.resultBufer = cliMsgData
                return 0
            else:
                raise ValueError("unknown cliHdr.msgType".format(res1.msgType))
        except ValueError as e:
            logger.debug("ValueError: {}: cmd: {}, res1: {}".format(e, command, res1))
            self.errstr = cliMsgData
            self.lastRcvd = res1
            self.lastRcvdCommand = command
            raise e
        # received one command
        self.resultBufer = ""
        del(self.__sent[res1.seqNum])
        return 1
    def __proces_cmds(self, cmds:  list):
#    def __proces_cmds(self, cmds , list):
        self.data = []
        self.resultBufer = ""
        self.errstr = None
        rtc = 0
        cmdsSent = 0
        cmdsRecv = 0
        seqWindow = self.seqWindow
        self.res1 = []

        try:
            cmdsSent = 0
            for command in cmds:
                self.__sendCommand(command, cmdsSent)
                cmdsSent = cmdsSent + 1

                if (cmdsSent - cmdsRecv) > seqWindow:
                    self.__waitMessage(1)
                    cmdsRecv += 1
            self.__waitMessage(cmdsSent - cmdsRecv)
        except ValueError as e:
            logger.debug("Exception {}".format(e))
            rtc = 2
            e.args = (e.args, self)
            self.exception = e
        except Exception as e:
            logger.error("Exception {}".format(e))
            self.data.append(None)
            self.errstr = "{}".format(e)
            rtc = 1
            e.args = e.args + ('process_cmds', self)
            self.exception = e
        return(Result(self.data, self.errstr, rtc))

    def __main_loop(self):
        while True:
            item = self.__inq.get()
            logger.debug("Got item {}".format(item))
            if item == -1:
                break
            if isinstance(item, Task):
                logger.debug("processing async task '{}'".format(item))
                self.pending.append(item)
                self.__process_task(item, self._e_task_done)
            else:
                logger.debug("processing sync cmd '{}'".format(item))
                self.__outq.put(self.__proces_cmds(item))

    def set_debug(self, *handlers, ecmd=True):
        # set logger level to debug and assign
        # handlers if provided

        self.exceptionOnCmdError = ecmd
        logger.setLevel(logging.DEBUG)
        for handler in handlers:
            logger.addHandler(handler)

    def close(self):
        """
           Close ITC communication
        """
        logger.debug("Closing communication: {}".format(self.sim))
        self.__inq.put(-1)

        for task in self.pending:
            task._task_state = "DONE"
        self.__main_loop.join()
        itcLib.closeFd(self.simItcContext)
        simList.remove(self)
        if len(simList) == 0 and itcLib is not None:
            itcLib.close()

    def cmd(self, cmd: list, timeout=-10):
        """method to execute sync command"""
        # logger.error("cmd: len {}".format(len(cmd)))
        self.__inq.put(cmd)
        if timeout == -10:
            timeout = self._defaultTimeout
        res = self.__outq.get(timeout=timeout)
        if self.errstr is not None and self.exceptionOnCmdError:
            raise self.exception
        return res

    def acmd(self, cmd: list, callback=None, timeout=-10):
        """method to execute async command"""
        logger.debug("in acmd")
        if timeout == -10:
            timeout = self._defaultTimeout
        t = Task(cmd, callback, self, timeout)
        self.__inq.put(t)
        return (t)

    def as_completed(self, tasks, timeout=-10):
        logger.debug("in as_completed")
        if timeout == -10:
            timeout = self._defaultTimeout
        endTime = time.time() + timeout if timeout else None
        remaining = list(tasks)
        for task in remaining:
            if task._sim != self:
                raise ValueError("task {} does not belog to this simulator {}".format(task, self))
        while len(remaining) > 0:
            ev = self._e_task_done.acquire(timeout=endTime - time.time() if timeout is not None else None)
            # ev = self._e_task_done.wait(timeout = endTime - time.time() if timeout != None else None)
            logger.debug("got event {} remaining {}".format(ev, len(remaining)))

            if not ev:
                # import pdb; pdb.set_trace()
                raise Timeout("Timeout: {}, len(remaining) {}".format(timeout, len(remaining)))
            # self._e_task_done.clear()

            if self.errstr is not None and self.exceptionOnCmdError:
                raise self.exception

            for task in remaining:
                if task.done():
                    remaining.remove(task)
                    yield task
            logger.debug("remaining {}".format(len(remaining)))
