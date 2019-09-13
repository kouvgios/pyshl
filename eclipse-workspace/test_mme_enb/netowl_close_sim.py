import time
import sys
import datetime
import logging
from functools import wraps
import traceback
import os
import pprint
import re
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



#import pdb; pdb.set_trace()


sim_expect = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.1 -t 127.0.0.2 --pgw-s5s8-address 172.0.0.3 --s5-type-gtp --enb-s1u-address 127.0.0.4 --enable-cli --itc-server 127.0.0.1:40 --inst-id 1" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim = {"name": "sim-mme-enb", "ip": "127.0.0.1" ,"port": 40, "instId": 1}



sim_expect2 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.2 -t 127.0.0.3 --pgw-s5s8-address 172.0.0.4 --s5-type-gtp --enb-s1u-address 127.0.0.5 --enable-cli --itc-server 127.0.0.2:8001 --inst-id 2" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim2 = {"name": "sim-mme-enb", "ip": "127.0.0.2" ,"port": 8001, "instId": 2}



sim_expect3 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.3 -t 127.0.0.4 --pgw-s5s8-address 172.0.0.5 --s5-type-gtp --enb-s1u-address 127.0.0.6 --enable-cli --itc-server 127.0.0.3:8002 --inst-id 3" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim3 = {"name": "sim-mme-enb", "ip": "127.0.0.3" ,"port": 8002, "instId": 3}


bash_expect = {'cmd': "bash", 'errPattern': r'(Command not found|No such file or directory|Operation not permitted|Permission denied)'}


def parse_argumets():
    global myPath# make mypath a global variable to use it anywhere

    kwargs1 = {}

    
    myPath = os.path.dirname(os.path.realpath(__file__))


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
                kwargs1['myInstId'] = int(getNextParam())
            elif (param == "--libPath"):
                kwargs1['itcLibraryPath'] = getNextParam()
            elif (param == "--cmd"):
                sim_expect['cmd'] = getNextParam()
            elif (param == "--prompt"):
                sim_expect['prompt'] = getNextParam()
            elif (param == "--target"):
                sim_expect['target'] = getNextParam()
                bash_expect['target'] = sim_expect['target']
            else:
                logger.error("Invalid argument: ", param)
    except ValueError:
        error("Invalid value specified after " + sys.argv[getNextParam.p - 2])

    logger.info("sim: {}".format(sim))
    logger.info("sim_expect: {}".format(sim_expect))
    logger.info("bash: {}".format(bash_expect))
    if kwargs1:
        logger.info("special init itcLibrary {}".format(kwargs1))
        itc.getItcLib(**kwargs1)



def exit2(retv=0):
    itc.close()
    itc_pexpect.close()
    
    
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


    except Exception as e:
        logger.error("Exception while executing intial shell commands : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(3)


def start_simulators():
    global mme_console
    global mme_console2
    global mme_console3
    
    
    global mme 
    global mme2
    global mme3

    try:
        # import pdb; pdb.set_trace()
        mme_console = itc_pexpect.Itc(sim_expect)
        mme_console2 = itc_pexpect.Itc(sim_expect2)
        mme_console3 = itc_pexpect.Itc(sim_expect3)

        mme = itc.Itc(sim)
        mme2 = itc.Itc(sim2)
        mme3 = itc.Itc(sim3)
        
        itc.getItcLib().netowl.pyapi_print_stats()
        import pdb; pdb.set_trace()
        



    except Exception as e:
        logger.error("Exception from startup : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(3)        



def test():
    logger.info("TEST START")
#    import pdb; pdb.set_trace() 
    import pdb; pdb.set_trace()
    try:
        
#       enable json ouput
        res1 = mme.cmd(["set json-file stdout"])
    
        pprint.pprint(res1.data)
        
        
        
        mme2.cmd(["set json-file stdout"])
        mme3.cmd(["set json-file stdout"])
#        mme_console3.cmd(["exit"])
    
    except Exception as e:
        logger.error("sim pexpect closed: {}".format(e))
        traceback.print_tb(e.__traceback__)
     
     
    import pdb; pdb.set_trace() 
    itc.close()   
    itc_pexpect.close()
    import pdb; pdb.set_trace()    
#'''reopen the sim'''        
#sim_expect = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.1 -t 127.0.0.2 --pgw-s5s8-address 172.0.0.3 --s5-type-gtp --enb-s1u-address 127.0.0.4 --enable-cli --itc-server 127.0.0.1:40 --inst-id 1" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
#sim = {"name": "sim-mme-enb", "ip": "127.0.0.1" ,"port": 40, "instId": 1}   
        
        
        
if __name__ == "__main__":
    parse_argumets()
    prepare_interfaces()
    start_simulators()
    
    
    
    

    try:
        test()
    except Exception as e:
        logger.error("Exception from test : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(5)

    exit2(0)   
     
