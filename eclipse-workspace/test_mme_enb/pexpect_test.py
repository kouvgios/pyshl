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
#import itc
import itc_pexpect # this module allows you to control other applications from python by expecting what they will do such as ssh , ftp ,passwd etc.
import subprocess
import itc
import ipaddress

sh = logging.StreamHandler()#

formatter = logging.Formatter('%(asctime)s - %(threadName)15s %(name)s '
                              'ln: %(lineno)d - %(levelname)s - %(message)s')
sh.setFormatter(formatter)
logging.root.addHandler(sh)
logging.root.setLevel(logging.DEBUG)

#################################################

#itcLib = None


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
#sim_expect = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.1 -t 127.0.0.2 --pgw-s5s8-address 172.0.0.3 --s5-type-gtp --enb-s1u-address 127.0.0.4 --enable-cli" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.1 -t 127.0.0.2 --pgw-s5s8-address 172.0.0.3 --s5-type-gtp --enb-s1u-address 127.0.0.4 --enable-cli --itc-server 127.0.0.1:8000 --inst-id 1" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}

sim = {"name": "sim-mme-enb", "ip": "127.0.0.1" ,"port": 8000, "instId": 1}


bash_expect = {'cmd': "bash", 'errPattern': r'(Command not found|No such file or directory|Operation not permitted|Permission denied)'}






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
#ask brano what geNextParam.p is?
#    import pdb; pdb.set_trace()
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
#    import pdb; pdb.set_trace()
#    logger.info("sim: {}".format(sim))
    logger.info("sim_expect: {}".format(sim_expect))




 

def exit2(retv=0):
    itc.close()
    itc_pexpect.close()
    import threading
    active_threads = threading.active_count()
    if active_threads > 1:
        logger.error("Warning there are more threads: {}".format(active_threads))
    exit(retv)

# def prepare_interfaces():
#     global bash
#     try:
#         bash = itc_pexpect.Itc(bash_expect)
#     except Exception as e:
#         logger.error("Exception from shell startup : {}".format(e))
#         traceback.print_tb(e.__traceback__)
#         exit2(3)
#     try:
#         # import pdb; pdb.set_trace()
#         res = bash.cmd(["echo $PS1", "hostname", "pwd"])
#         logger.info("bash expect: %s" % res.data)
#         with open("%s/bash_veth.txt" % myPath) as f:
#             lines = f.read().splitlines()
#             f.close()
#             res = bash.cmd(lines)
#             logger.info(res.data)
#     except Exception as e:
#         logger.error("Exception while executing intial shell commands : {}".format(e))
#         traceback.print_tb(e.__traceback__)
#         exit2(3)


def start_simulators():
    global mme_console
    global mme

    
    
    


def test():
    logger.info("TEST START")
    
    try:
#        import pdb; pdb.set_trace() 
        mme_console = itc_pexpect.Itc(sim_expect)
        res = mme_console.cmd(["show version","show log-level","show log"])
        logger.info("mme_console: %s" % res.data)
                
        mme = itc.Itc(sim)
###attach a session###       
        mme.cmd(["create profile 1"])
        mme.cmd(["set profile 1 apn ipd.alcatel-lucent.com"])
        mme.cmd(["set profile 1 imsi 123456789012915"])
        mme.cmd(["set profile 1 pdn-type 6"])
        mme.cmd(["set profile 1 bearer-context 6,15,8,1000000,1000000,0,0"])
        mme.cmd(["set profile 1 mei 987654321012399"])
        mme.cmd(["set profile 1 timezone 32"])
        mme.cmd(["set profile 1 apn-ambr 5000,5000"])
        mme.cmd(["set profile 1 pco 8080210a0144000a810600000000"])
        mme.cmd(["set profile 1 cbresp-cause 16"])
        mme.cmd(["set profile 1 dbresp-cause 16"])
        mme.cmd(["set profile 1 retry-count 1"])
        mme.cmd(["set profile 1 retry-time 5"])
        mme.cmd(["set profile 1 hrpd-attach false"])
        mme.cmd(["set profile 1 max-burst-rate 50"])
        mme.cmd(["set profile 1 piggyback-flag false"])
        mme.cmd(["set profile 1 selection-mode 0"])
        mme.cmd(["set profile 1 apn-restriction-type 0"])
        mme.cmd(["set profile 1 break-piggyback-resp false"])
        mme.cmd(["set profile 1 ignore-piggyback-req false"])
        mme.cmd(["set profile 1 static-paa false"])
        mme.cmd(["set profile 1 ipv4-address-pool-prefix 100.0.0.0/24"])
        mme.cmd(["set profile 1 ipv6-address-pool-prefix 4ffe:6400::0/64"])
        mme.cmd(["set profile 1 ipv6-address-pool-size 1024"])
        mme.cmd(["set profile 1 default-bearer-context 5,15,9,1000000,1000000,0,0"])
        mme.cmd(["set profile 1 no-imsi false"])
        mme.cmd(["set profile 1 unauth-imsi false"])
        mme.cmd(["set profile 1 ipv4-address-pool-size 256"])
        mme.cmd(["set profile 1 csg-cr-support true"])
        mme.cmd(["set profile 1 auto-failed-reattach-delay 0"])
        mme.cmd(["set profile 1 uli-mcc-mnc-ecgi 123456,0x1234567"])
        mme.cmd(["set profile 1 msisdn 12345098761"])
        mme.cmd(["set profile 1 uli-cr-support true"])
        mme.cmd(["create session-group 1 1 1"])
        mme.cmd(["proc attach group 1"])
        mme.cmd(["show session-group 1 count"])
        mme.cmd(["show session-group 1 count"])
        import pdb; pdb.set_trace() 
        res = mme.cmd(["show log","show session-group 1","show profile 1","show version","show log-level"])
        logger.info("mme: %s" % res.data) 

    except Exception as e:
        logger.error("Exception from startup : {}".format(e))
        
        traceback.print_tb(e.__traceback__)
        exit2(2)
        


        

if __name__ == "__main__":
#    prepare_interfaces()
    start_simulators()

    try:
        test()
    except Exception as e:
        logger.error("Exception from test : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(5)
        
    exit2(0)   






