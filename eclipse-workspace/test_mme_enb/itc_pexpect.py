import queue
import threading
import logging
from collections import namedtuple
import time
import pexpect
import json
import re
# import pprint

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.ERROR)
# logger.setLevel(logging.DEBUG)


# Task = namedtuple("Task", ("id", "name", "callback"))
Result = namedtuple("Result", ("data", "estr", "rtc"))
MsgResult = namedtuple("MsgResult", ("msgType", "msgOptions", "seqNum", "data"))

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
#        self._sim2 = sim2
    def __str__(self):
        return str(vars(self))

    def done(self):
        return "DONE" in self._task_state

    def __set_state(self, state):
        self.__task_state = state

    @property
    def callback(self):
        return(self.__callback)

    @property
    def id(self):
        return(self.__id)

    @property
    def state(self):
        return(self.__task_state)

    @property
    def cmd(self):
        return(self.__cmd)

    @property
    def result(self):
        return self._result


def close():
    while len(simList) > 0:
        sim = simList[-1]
        logger.debug("close:sim: {}, simlist: {}".format(sim, simList))
        sim.close()


class Itc(object):

    def __init__(self, sim, defaultTimeout=30):
        logger.info("Itc: connecting to {}".format(sim))
#        logger.info("Itc: connecting to {}".format(sim2))
        # self.exceptionOnCmdError = False
        self.exceptionOnCmdError = True
        self._defaultTimeout = defaultTimeout
        self.__inq = queue.Queue()
        self.__outq = queue.Queue()
        self.seqNumS = 0
        self.seqNumR = 0
        self.seqWindow = 0
        self._e_task_done = threading.Semaphore(0)
        self.__sent = {}
        self.sim = sim
#        self.sim2 = sim2
        cmd = sim.get('cmd', "")
#        cmd = sim2.get('cmd', "")
        shell = sim.get('shell', "")
#        shell = sim2.get('shell', "")
        prompt = sim.get('prompt')
#        prompt = sim2.get('prompt')
        target = sim.get('target')
#        target = sim2.get('target')
        self.errPattern = sim.get('errPattern', r'(ERROR:|CLI was expecting:|Command not found|No such file or directory|Operation not permitted|Permission denied)')
        if not shell:
            # fix shell when remote cmd
            if target:
                shell = "ssh"
                if cmd == "ssh" or cmd == "bash":
                    cmd = ""
            elif not cmd or cmd == "bash":
                shell = "bash"
                cmd = ""
        # shell_prompt is usefull to detect if command with its own prompt failed. For others it is EOF that is matched before
        self.shell_prompt = pexpect.EOF
        if target:
            if cmd and not prompt:
                # one shot command over ssh
                command = "%s %s '%s'" % (shell, target, cmd)
                return self.one_shot_cmd(command)
            else:
                # program with its own prompt needs shell
                command = "%s %s" % (shell, target)
                self.spawnWaitPrompt(command, None)
                if cmd and prompt:
                    self.shell_prompt = self.prompt
                    self.prompt = prompt
                    res = self.__proces_cmds([cmd])
                    if res.estr is not None:
                        raise self.exception
        else:
            if shell:
                command = "%s %s" % (shell, cmd)
                self.spawnWaitPrompt(command, prompt)
            elif prompt:
                command = cmd
                self.spawnWaitPrompt(command, prompt)
            else:
                command = 'bash -c "%s"' % re.escape(cmd)
                return self.one_shot_cmd(command)

        # finish startup
        self.pending = []
        self.__main_loop = self.__start()
        simList.append(self)

    def spawnWaitPrompt(self, command, prompt):

        self.simItcContext = pexpect.spawn(command)
        if not self.simItcContext:
            logger.error("Cannot spawn: %s, sim: %s" % (command, self.sim))
            raise ValueError("Cannot spawn: %s, sim: %s" % (command, self.sim))
        logger.info("spawned command: {}\r\nIct_pexpect pid: {}".format(command, self.simItcContext.pid))
        self.simItcContext.setwinsize(400,400)

        if not prompt:
            # set prompt to easy to parse value
            self.prompt = r'(>|#|\$)'
            i = self.simItcContext.expect([self.prompt, pexpect.EOF, pexpect.TIMEOUT])
            if i == 1:
                raise ValueError("EOF before weak prompt. (command: %s, result: %s, expected: %s)" % (command, self.simItcContext.before, self.prompt))
            elif i == 2:
                raise ValueError("Timeout before weak prompt. (command: %s, result: %s, expected: %s)" % (command, self.simItcContext.before, self.prompt))
            # ##logger.debug("Got weak prompt: before: %s, match: '%s', expected: %s" % (self.simItcContext.before, self.simItcContext.match.group(), self.prompt))

            # set prompt to something constant
            self.prompt = "==__prompt_pid_%s__== " % self.simItcContext.pid
            cmd1 = "PROMPT_COMMAND=;PS1=\"%s\"" % self.prompt
            self.simItcContext.sendline(cmd1)
            i = self.simItcContext.expect([cmd1, pexpect.EOF, pexpect.TIMEOUT])
            if i == 1:
                raise ValueError("EOF before got cmd1. (command: %s, result: %s, expected: %s)" % (command, self.simItcContext.before, cmd1))
            elif i == 2:
                raise ValueError("Timeout before got cmd1. (command: %s, result: %s, expected: %s)" % (command, self.simItcContext.before, cmd1))
            # ##logger.debug("Got cmd1: %s, before: %s," % (self.simItcContext.match.group(), self.simItcContext.before))
        else:
            # command executed with own prompt
            self.prompt = prompt

        # wait for first prompt
        i = self.simItcContext.expect([self.prompt, pexpect.EOF, pexpect.TIMEOUT])
        if i == 1:
            raise ValueError("EOF before prompt. (command: %s, result: %s, expected: %s)" % (command, self.simItcContext.before, self.prompt))
        elif i == 2:
            raise ValueError("Timeout before prompt. (command: %s, result: %s, expected: %s)" % (command, self.simItcContext.before, self.prompt))
        logger.debug("Got prompt command: %s, before: %s, expected: %s," % (command, self.simItcContext.before, self.prompt))

    def one_shot_cmd(self, command):

        self.simItcContext = pexpect.spawn(command)

        logging.error(" one shot (no shell, no prompt) shell: %s, cmd: %s, t: %s, c: %s" % (self.sim.get("shell"), self.sim.get("cmd"), self.sim.get("target"), command))
        i = self.simItcContext.expect([pexpect.EOF, pexpect.TIMEOUT])
        if i == 0:
            cliMsgData = self.simItcContext.before.decode("utf-8")
            self.__sent[0] = command
            result = MsgResult(1, 0, 0, cliMsgData)
            self.res1.append(result)
            self.__process_res1(self.res1[-1])
            return
        elif i == 2:
            raise ValueError("One shot command timeout before EOF: %s" % self.simItcContext.before.decode("utf-8"))

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
        if cmdsSent <= 0:
            self.firstSeqNum = seqNum

        self.simItcContext.sendline(command)
        self.__sent[seqNum] = command
        self.seqNumS = seqNum

    def __waitMessage(self, num):
        resIdx = len(self.data)
        expectedIdx = resIdx + num
        while resIdx < expectedIdx:
            self.seqNumR = self.firstSeqNum + resIdx
            command = self.__sent[self.seqNumR]
            msgType = 2
            i = self.simItcContext.expect([re.escape(command), pexpect.EOF, pexpect.TIMEOUT])
            if i == 1:
                cliMsgData = "EOF earlier than cmd: %s, before: %s," % (re.escape(command), self.simItcContext.before)
            elif i == 2:
                cliMsgData = "Timeout earlier than cmd: %s, before: %s," % (re.escape(command), self.simItcContext.before)
            elif i == 0:
                # ##logger.debug("Got command: %s, before: %s," % (self.simItcContext.match.group(), self.simItcContext.before))
                i = self.simItcContext.expect([self.prompt, pexpect.EOF, pexpect.TIMEOUT, self.shell_prompt])
                if i == 1:
                    cliMsgData = "EOF before prompt: %s" % self.simItcContext.before.decode("utf-8")
                elif i == 2:
                    cliMsgData = "Timeout before prompt: %s" % self.simItcContext.before.decode("utf-8")
                elif i == 3:
                    cliMsgData = "Returned back to original shell: %s" % self.simItcContext.before.decode("utf-8")
                elif i == 0:
                    # ##logger.debug("Got prompt: %s, before: %s, expected: %s," % (self.simItcContext.match.group(), self.simItcContext.before, self.prompt))
                    cliMsgData = self.simItcContext.before.decode("utf-8")
                    searchObj = re.search(self.errPattern, cliMsgData)
                    # import pdb; pdb.set_trace()
                    if not searchObj:
                        msgType = 1
            result = MsgResult(msgType, 0, self.seqNumR, cliMsgData)
            self.res1.append(result)

            self.__process_res1(self.res1[resIdx])
            resIdx += 1

    def __process_res1(self, res1):
        if res1 == -1:
            raise Timeout()
        cliMsgData = res1.data
        # big slow down even if debug is turned off
        # logger.debug("recv from workQueue: seqNumS: {}, res1: {}".format(self.seqNumS, res1))
        try:
            command = self.__sent[res1.seqNum]
            del(self.__sent[res1.seqNum])

            if res1.msgType == 2:
                raise ValueError("sim failed to execute", command, cliMsgData)
            elif res1.msgType == 1:
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
            else:
                raise ValueError("unknown cliHdr.msgType")
        except ValueError as e:
            logger.debug("ValueError: {}: cmd: {}, res1: {}".format(e, command, res1))
            self.errstr = cliMsgData
            self.lastRcvd = res1
            self.lastRcvdCommand = command
            raise e

#    def __proces_cmds(self, cmds: list):
    def __proces_cmds(self, cmds: list):    
        self.data = []
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
            # import pdb; pdb.set_trace()
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
        logger.debug("end of __main_loop")

    def set_debug(self, *handlers, ecmd=True):
        # set logger level to debug and assign
        # handlers if provided

        self.exceptionOnCmdError = ecmd
        logger.setLevel(logging.DEBUG)
        for handler in handlers:
            logger.addHandler(handler)

    def close(self):
        """
           Close pexpect
        """
        logger.debug("Closing itc_pexpect: {}".format(self.sim))
        self.__inq.put(-1)

        for task in self.pending:
            task._task_state = "DONE"
        self.__main_loop.join()
        logger.debug("__main_loop ended")
        # 2#itcLib.closeFd(self.simItcContext)
        # import pdb; pdb.set_trace()
        self.simItcContext.sendline()#change lines and specifically defines the  new line (\n)
        self.simItcContext.sendline("exit")
        self.simItcContext.expect([pexpect.EOF, pexpect.TIMEOUT], timeout = 10)
        self.simItcContext.close(force=True)
        simList.remove(self)
        logger.debug("itc_pexpect close end")

    def cmd(self, cmd: list, timeout=-10):
        """method to execute sync command"""
        # logger.error("cmd: len {}".format(len(cmd)))
        self.__inq.put(cmd)
        if timeout == -10:
            timeout = self._defaultTimeout
        res = self.__outq.get(timeout=timeout)
        # res = self.__outq.get()
        if res.estr is not None and self.exceptionOnCmdError:
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
