import time
import sys
import datetime
import logging
from functools import wraps
import traceback
import os
import pprint
import ipaddress
from ctypes.test.test_random_things import callback_func

sys.path.append('/opt/netowl/python3_packages')
import itc
import itc_pexpect # this module allows you to control other applications from python by expecting what they will do such as ssh , ftp ,passwd etc.

sh = logging.StreamHandler()#

formatter = logging.Formatter('%(asctime)s - %(threadName)15s %(name)s '
                              'ln: %(lineno)d - %(levelname)s - %(message)s')
sh.setFormatter(formatter)
logging.root.addHandler(sh)
logging.root.setLevel(logging.DEBUG)

#################################################

def error(s):
        print("-E-" * 15)
        print("ERROR:", s)
        print("-E-" * 15)
        print("ARGUMENTS: " + ", ".join(sys.argv))
        printHelp()
        exit()


class ParamError(Exception):  #Python provides two very important features to handle any unexpected error in your Python programs and to add debugging capabilities in them
    def __init__(self, arg):  #exception for errors we expect like file not found e.g
        self.args = arg

logger = logging.getLogger(__name__)
# gets next system argument
def getNextParam():
    if (getNextParam.p > (len(sys.argv) - 1)):
        raise ParamError("no more params") #with raise parameter you can manually raise exception or error in some other def
    param = sys.argv[getNextParam.p]  #sys.argv is a list in Python, which contains the command-line arguments passed to the script. 
    '''
    #With the len(sys.argv) function you can count the number of arguments. 
    #If you are gonna work with command line arguments, you probably want to use sys.argv.
    #To use sys.argv, you will first have to import the sys module. 
    '''
    getNextParam.p += 1
    return param



def printHelp(): #The help() method calls the built-in Python help system and the above is the noxia description output
    print(
        """test_mme_enb.py [--cmd <commnd_to_start_simulator>] [--prompt <simulator_prompt>] [--target <user@host>]
        [--sim <simulator-name>] [--simInstId <number>] [--ip simIpAddress] [--port simItcPort] [--instId <number>] [--libPath <pathToItcLibrary>]
    Sample netowl itc python api and itc_pexpect python api program.
    e.g.: sudo ./test_mme_enb.py  # run simple sim-mme-enb test locally
    e.g.: ./test_mme_enb.py  --ip 135.243.194.249 --target root@135.243.194.249 # run remotely over ssh on target with authorized keys
    e.g.: sudo ./test_mme_enb.py  --cmd "netowl/_build/release-x86_64-native-dpdk/sim-mme-enb --itc-server 0.0.0.0:8000" # running sim-mme-enb locally from build directory\n""")



'''new sim parameters list'''
# mme = {"name": "sim-mme-enb", "ip": "127.0.0.1" ,"port": 8000, "instId": 1}    
sim_list =[]
sim_expect_list=[]
for i in  range(0, 15):
    srvIp = str(ipaddress.IPv4Address('127.0.0.1')+i)
    sim_list.append({"name": "sim-mme-enb", "ip": srvIp ,"port": 8000+i, "instId": 1+i})





bash_expect = {'cmd': "bash", 'errPattern': r'(Command not found|No such file or directory|Operation not permitted|Permission denied)'}
# bash_expect = {'cmd' : "bash", 'errPattern':r'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}


mme = {"name": "sim-mme-enb", "ip": "127.0.0.1" ,"port": 8000, "instId": 1}
#mme.append(itc.itc(mme))

#new sim bash command and arguments to start sim
#import pdb; pdb.set_trace()
for i in  range(0, 2):
    sim_expect_list.append({ 'cmd': "/opt/netowl/bin/sim-mme-enb -d {} -t {} --pgw-s5s8-address {} --s5-type-gtp --enb-s1u-address {} --enable-cli --itc-server {}:{} --inst-id {}".format(sim_list[i]["ip"],sim_list[i+1]["ip"],sim_list[i+2]["ip"],sim_list[i+3]["ip"],sim_list[i]["ip"],sim_list[i]["port"],sim_list[i]["instId"]),'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'})
 
for i in range(2, 15):
#    for j in range(1, 4):
    srvIp1 = str(ipaddress.IPv4Address(sim_list[i]["ip"])+1)
    srvIp2 = str(ipaddress.IPv4Address(sim_list[i]["ip"])+2)
    srvIp3 = str(ipaddress.IPv4Address(sim_list[i]["ip"])+3)        
    sim_expect_list.append({ 'cmd': "/opt/netowl/bin/sim-mme-enb -d {} -t {} --pgw-s5s8-address {} --s5-type-gtp --enb-s1u-address {} --enable-cli --itc-server {}:{} --inst-id {}".format(sim_list[i]["ip"],srvIp1,srvIp2,srvIp3,sim_list[i]["ip"],sim_list[i]["port"],sim_list[i]["instId"]),'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'})





'''old sim parameters list'''
def parse_argumets():
    global myPath# make mypath a global variable to use it anywhere
 
    kwargs1 = {}
 
    # directory where this script is located
    myPath = os.path.dirname(os.path.realpath(__file__))
 
#ask brano if no arguments then print help    
    # process arguments
    if (len(sys.argv) < 0):  
        printHelp()
        exit()


def exit2(retv=0):
    itc.close()
    itc_pexpect.close()
    import threading
    active_threads = threading.active_count()
    if active_threads > 1:
        logger.error("Warning there are more threads: {}".format(active_threads))
    exit(retv)



def prepare_interfaces():
    global bash
    try:
        bash = itc_pexpect.Itc(bash_expect)
    except Exception as e:
        logger.error("Exception from shell startup : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(3)
    try:
        # import pdb; pdb.set_trace()
        res = bash.cmd(["echo $PS1", "hostname", "pwd"])
        logger.info("bash expect: %s" % res.data)

#        with open("%s/bash_veth.txt" % myPath) as f:
#            lines = f.read().splitlines()
#            f.close()
#            res = bash.cmd(lines)
#            logger.info(res.data)
    except Exception as e:
        logger.error("Exception while executing intial shell commands : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(3)
        
        
        
def start_simulators():



    '''new start sims'''
    
    global sim_list 
    global mme_console_list
    global mme_list
    global mme
            
# #   import pdb; pdb.set_trace()
    try:
         
         
        mme_console_list=[]
        mme_list=[]
#        mme
        
        for i in range(0, 15):  
            mme_console_list.append(itc_pexpect.Itc(sim_expect_list[i]))
            mme_list.append(itc.Itc(sim_list[i]))
     
    except Exception as e:
        logger.error("Exception from startup : {}".format(e))
        traceback.print_tb(e.__traceback__)
        
        exit2(3)


def test():
    logger.info("TEST START")
    
    
    

    

    '''check wrong cmd format'''
    try:
        
        
        for i in range(0, 15):
            mme_list[i].cmd(["show version","trigger error","show log-level"])
            mme_list[i].cmd(["show config"])
            logger.info(mme_list[i].data[0])

    except Exception as e:
        logger.error("I have exception which is ok now as we are testing if 'trigger error' command triggers exception Exception {}".format(e))
        traceback.print_tb(e.__traceback__)
        
#       enable json ouput
        
        for i in range(0, 15):
            mme_list[i].cmd(["set json-file stdout"])

    
    def timeit(fn):
        @wraps(fn)
        def rate(*args, **kwargs):
            start = datetime.datetime.now()
            res = fn(*args, **kwargs)
#            res1= fn(*args, **kwargs)
#            res3 = fn(*args, **kwargs)
            
            end = datetime.datetime.now()
            return (res, (end - start).total_seconds())
        return rate
    
        
    @timeit
    def iterationtest1(iterations):
        while iterations >= 0:
            mme_list[i].cmd(["show version"])
#           mme2.cmd(["show version"])
#            mme3.cmd(["show version"])
            iterations -= 1
    
    iterations = 1
    logger.debug("Iteration test1_1_cmd")
    res, time = iterationtest1(iterations)
    logger.debug("rate {} iter/s ".format((iterations / time ,res)))
    logger.debug("End Iteration test1_1_cmd, time {}".format(time))
#    logger.debug("{}".format(len(res.data)))
    
    @timeit
    def iterationtest1_7000sessions(iterations):
        while iterations >= 0:
            mme_list[i].cmd(["show version"])

            iterations -= 1
    
    iterations = 7000
    logger.debug("Iteration test1_7000_cmds")
    res, time = iterationtest1(iterations)
    logger.debug("rate {} iter/s ".format((iterations / time ,res)))
    logger.debug("End Iteration test1_7000_cmds, time {}".format(time))

    
    '''With yield and genarators is 1/3 of the time'''   
    @timeit
    def itertest2(iterations):
        def gen(iterations):
            while iterations > 0:
                yield "show version"
#               yield "show log-level"
                iterations -= 1
        return(mme_list[i].cmd(gen(iterations)))
    
    
    iterations = 1
    logger.debug("Iteration test2_1_cmd")
    res, time = itertest2(iterations)
    logger.debug("rate {} iter/s".format((iterations / time)))
    logger.debug("End Iteration test2_1_cmd ,time {} ".format(time))
    logger.debug("{}".format(len(res.data)))
    
    @timeit
    def itertest2_7000_cmds(iterations):
        def gen(iterations):
            while iterations > 0:
                yield "show version"
#               yield "show log-level"
                iterations -= 1
        return(mme_list[i].cmd(gen(iterations)))
    
    
    iterations = 7000
    logger.debug("Iteration test2_7000_cmds")
    res, time = itertest2(iterations)
    logger.debug("rate {} iter/s".format((iterations / time)))
    logger.debug("End Iteration test2_7000_cmds ,time {} ".format(time))
    logger.debug("{}".format(len(res.data)))

    
    
    @timeit
    def itertest3_7000(iterations,i):
        global tasks1
        global tasks2
        global tasks3
        
        def gen(iterations):
            while iterations > 0:
                yield "show version"
#                yield "show log-level"
                iterations -= 1
        it = 0
        tasks1 = list()
        tasks2 = list()
        tasks3 = list()
        tasks1.append(mme_list[i].acmd(gen(iterations)))
        tasks1.append(mme_list[i].acmd(gen(iterations)))
        tasks1.append(mme_list[i].acmd(gen(iterations)))
        tasks2.append(mme_list[i].acmd(gen(iterations)))
        tasks2.append(mme_list[i].acmd(gen(iterations)))
        tasks2.append(mme_list[i].acmd(gen(iterations)))
        tasks3.append(mme_list[i].acmd(gen(iterations)))
       
        for task in mme_list[i].as_completed(tasks1, timeout=5):
            it = 0
            it += len(task.result.data)
            logger.info("it {}".format(it))
            logger.info("Tasks1 completed {}".format(len(tasks1))) 
            
#           import pdb; pdb.set_trace()
        
        for task in mme_list[i].as_completed(tasks2 ,timeout=5):
            it = 0
            it += len(task.result.data)
  
            logger.debug("it {}".format(it))
            logger.info("Tasks2 completed {}".format(len(tasks2)))
             
        for task in mme_list[i].as_completed(tasks3 ,timeout=5):
            it = 0
            it += len(task.result.data)
            logger.debug("it {}".format(it))
            logger.info("Tasks3 completed {}".format(len(tasks3)))
             
        return(it)      

    
    iterations = 7000
    logger.debug("Iteration test3")
    
    
    for j in range (0,5) :
        print("iteration:{}".format(j)) 
        res, time = itertest3_7000(iterations,i)
        logger.debug("rate {} iter/s (iterations {})".format((res / time), res))
        logger.debug("End Iteration test3_7000cmds {} ".format(time))   

    
    tasks = list()
 

    tasks.append(mme_list[i].acmd(["show version"]))

     
    logger.info("Tasks {}".format(tasks))
    print("Number of tasks is :",(len(tasks)))
    pprint.pprint(len(tasks))

             
        
        



    
    '''add fileHandler'''
    fh = logging.FileHandler('/tmp/mytestdebug')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    

    @timeit
    def itertest3_1_cmd(iterations):
        global tasks1

        def gen(iterations):
            while iterations > 0:
                yield "show version"
#                yield "show log-level"
        
                iterations -= 1
        
        it = 0
        tasks1 = list()
        
        tasks1.append(mme_list[i].acmd(gen(iterations)))

       
        for task in mme_list[i].as_completed(tasks1, timeout=5):
#            it = 0
            it += len(task.result.data)
            logger.info("it {}".format(it))
            logger.info("Tasks1 completed {}".format(len(tasks1))) 
            
                
        return(it)      

    iterations = 1
    logger.debug("Iteration test3_1_cmd")
    
    for j in range (0,5) :
        print("iteration:{}".format(j))
        
        res, time = itertest3_1_cmd(iterations)
        logger.debug("rate {} iter/s (iterations {})".format((res / time), res))
        logger.debug("End Iteration test3_1_cmd {} ".format(time))   
    
    

    
    
    '''callback testing'''
    

    def my_callback1(task):
        logger.info("Calling callback on task {}".format(task))
        logger.info("Task {} returned {}".format(task, res))
       
        '''waiting for task as they are being completed'''
        try:
            for task in mme_list[i].as_completed(tasks, timeout=5):
                res1 = task.result
                logger.info("callback Task result {}".format(res1))
           
           
#             for task in mme_list[i].as_completed(tasks3 ,timeout=5):
#                 res3 = task.result
#                 logger.info("callback Task2 result {}".format(res3)) 
              
#             for task in mme_list[i].as_completed(tasks3 ,timeout=5):
#                 res = task.result
#                 logger.info("callback Task3 result {}".format(res))     
               
#                import pdb; pdb.set_trace()       
               
        except itc.Timeout as e:
            logger.error("Timeout {}".format(e))
            # pass
        except Exception as e:
            logger.error("{}".format(e))
       
            # assign callback to task
            logger.info("Call backs")
             
            
              
#     iterations = 1000
#     logger.debug("Iteration test4")
#     res, time = (iterations)
#     logger.debug("rate {} iter/s (iterations {})".format((res / time), res))
#     logger.debug("End Iteration test4 {} ".format(time))       
# #import pdb; pdb.set_trace()
#    1(tasks)    
#    itertest3(1)       
    
#     logger.info("Tasks {}".format(tasks))
#     print("Number of tasks is :",(len(tasks))) 
     
       
#    import pdb; pdb.set_trace()
#    1(tasks)    

#   1(tasks)    
    
    
if __name__ == "__main__":
#    parse_argumets()
    prepare_interfaces()
    start_simulators()

    try:
        test()
    except Exception as e:
        logger.error("Exception from test : {}".format(e))
        traceback.print_tb(e.__traceback__)
        
        exit2(5)
    logger.info("TEST STOP")
    exit2(0)
