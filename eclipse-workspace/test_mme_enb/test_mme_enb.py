#!/usr/bin/env python3


import time
import sys
import datetime
import logging#imports the logging module in which can add logging details and activate logs
from functools import wraps
import traceback
import os
import pprint

sys.path.append('/opt/netowl/python3_packages')
import itc
import itc_pexpect # this module allows you to control other applications from python by expecting what they will do such as ssh , ftp ,passwd etc.
'''
#The pprint module provides a capability to “pretty-print” arbitrary Python data structures in a form which can be used as input to the interpreter. 
#If the formatted structures include objects which are not fundamental Python types, the representation may not be loadable. 
#This may be the case if objects such as files, sockets or classes are included, as well as many other objects which are not representable as Python literals.
#pp = pprint.PrettyPrinter(indent=4)
# pp.pprint(res2.data)

#Loggers expose the interface that application code directly uses.
#Handlers send the log records (created by loggers) to the appropriate destination.
#The StreamHandler class, located in the core logging package, sends logging output to streams such as sys.stdout, sys.stderr or any file-like object (or, more precisely, any object which supports write() and flush() methods).
'''
sh = logging.StreamHandler()#
#Formatters specify the layout of log records in the final output.
formatter = logging.Formatter('%(asctime)s - %(threadName)15s %(name)s '# is the time the name and the name of the log 
                              'ln: %(lineno)d - %(levelname)s - %(message)s')
sh.setFormatter(formatter)
logging.root.addHandler(sh)#for output of the logs
logging.root.setLevel(logging.DEBUG)#debug level of logs
'''
#Loggers have the following attributes and methods. 
#Note that Loggers are never instantiated directly, but always through the module-level function logging.getLogger(name). 
#Multiple calls to getLogger() with the same name will always return a reference to the same Logger object.
'''
logger = logging.getLogger(__name__)
# fh = logging.FileHandler('/tmp/{}.{}'.format(test.__name__, subtest_fn.__name__),
#                          mode='w')

'''
#################################################
##print exception in python
#Errors detected during execution are called exceptions and are not unconditionally fatal: you will soon learn how to handle them in Python programs. 
#Most exceptions are not handled by programs, however, and result in error messages as shown here:
'''
def error(s):
        print("-E-" * 15)
        print("ERROR:", s)
        print("-E-" * 15)
        print("ARGUMENTS: " + ", ".join(sys.argv))
        printHelp()
        exit()


'''
#self        
#the self variable represents the instance of the object itself. 
#Most object-oriented languages pass this as a hidden parameter to the methods defined on an object; Python does not. 
#You have to declare it explicitly.
'''
'''
#The __init__ method is roughly what represents a constructor in Python. (initializes data instances such as arg)
#When you call A() Python creates an object for you, and passes it as the first parameter to the __init__ method. 
#Any additional parameters
'''
'''
#class
#Objects get their variables and functions from classes. Classes are essentially a template to create your objects.
#they allow to logically group our data and functions (attributes and methods) 
# raised form getNextParam
'''
class ParamError(Exception):  #Python provides two very important features to handle any unexpected error in your Python programs and to add debugging capabilities in them
    def __init__(self, arg):  #exception for errors we expect like file not found e.g
        self.args = arg


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
sim_expect = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.1 -t 127.0.0.2 --pgw-s5s8-address 172.0.0.3 --s5-type-gtp --enb-s1u-address 127.0.0.4 --enable-cli --itc-server 127.0.0.1:8000 --inst-id 1" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect2 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.2 -t 127.0.0.3 --pgw-s5s8-address 172.0.0.4 --s5-type-gtp --enb-s1u-address 127.0.0.5 --enable-cli --itc-server 127.0.0.2:8001 --inst-id 2" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect3 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.3 -t 127.0.0.4 --pgw-s5s8-address 172.0.0.5 --s5-type-gtp --enb-s1u-address 127.0.0.6 --enable-cli --itc-server 127.0.0.3:8002 --inst-id 3" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect4 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.4 -t 127.0.0.5 --pgw-s5s8-address 172.0.0.6 --s5-type-gtp --enb-s1u-address 127.0.0.7 --enable-cli --itc-server 127.0.0.4:8003 --inst-id 4" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect5 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.5 -t 127.0.0.6 --pgw-s5s8-address 172.0.0.7 --s5-type-gtp --enb-s1u-address 127.0.0.8 --enable-cli --itc-server 127.0.0.5:8004 --inst-id 5" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect6 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.6 -t 127.0.0.7 --pgw-s5s8-address 172.0.0.8 --s5-type-gtp --enb-s1u-address 127.0.0.9 --enable-cli --itc-server 127.0.0.6:8005 --inst-id 6" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect7 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.7 -t 127.0.0.8 --pgw-s5s8-address 172.0.0.11 --s5-type-gtp --enb-s1u-address 127.0.0.10 --enable-cli --itc-server 127.0.0.7:8006 --inst-id 7" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect8 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.8 -t 127.0.0.9 --pgw-s5s8-address 172.0.0.12 --s5-type-gtp --enb-s1u-address 127.0.0.11 --enable-cli --itc-server 127.0.0.8:8007 --inst-id 8" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect9 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.9 -t 127.0.0.10 --pgw-s5s8-address 172.0.0.13 --s5-type-gtp --enb-s1u-address 127.0.0.12 --enable-cli --itc-server 127.0.0.9:8008 --inst-id 9" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect10 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.10 -t 127.0.0.11 --pgw-s5s8-address 172.0.0.14 --s5-type-gtp --enb-s1u-address 127.0.0.13 --enable-cli --itc-server 127.0.0.10:8009 --inst-id 10" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect11 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.11 -t 127.0.0.12 --pgw-s5s8-address 172.0.0.15 --s5-type-gtp --enb-s1u-address 127.0.0.14 --enable-cli --itc-server 127.0.0.11:8010 --inst-id 11" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect12 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.12 -t 127.0.0.13 --pgw-s5s8-address 172.0.0.16 --s5-type-gtp --enb-s1u-address 127.0.0.15 --enable-cli --itc-server 127.0.0.12:8011 --inst-id 12" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect13 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.13 -t 127.0.0.14 --pgw-s5s8-address 172.0.0.17 --s5-type-gtp --enb-s1u-address 127.0.0.16 --enable-cli --itc-server 127.0.0.13:8012 --inst-id 13" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect14 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.14 -t 127.0.0.15 --pgw-s5s8-address 172.0.0.18 --s5-type-gtp --enb-s1u-address 127.0.0.17 --enable-cli --itc-server 127.0.0.14:8013 --inst-id 14" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
sim_expect15 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.15 -t 127.0.0.16 --pgw-s5s8-address 172.0.0.19 --s5-type-gtp --enb-s1u-address 127.0.0.18 --enable-cli --itc-server 127.0.0.15:8014 --inst-id 15" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}
#sim_expect16 = { 'cmd': "/opt/netowl/bin/sim-mme-enb -d 127.0.0.16 -t 127.0.0.17 --pgw-s5s8-address 172.0.0.20 --s5-type-gtp --enb-s1u-address 127.0.0.19 --enable-cli --itc-server 127.0.0.16:8015 --inst-id 16" ,'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'}


sim = {"name": "sim-mme-enb", "ip": "127.0.0.1" ,"port": 8000, "instId": 1}
sim2 = {"name": "sim-mme-enb", "ip": "127.0.0.2" ,"port": 8001, "instId": 2}
sim3 = {"name": "sim-mme-enb", "ip": "127.0.0.3" ,"port": 8002, "instId": 3}
sim4 = {"name": "sim-mme-enb", "ip": "127.0.0.4" ,"port": 8003, "instId": 4}
sim5 = {"name": "sim-mme-enb", "ip": "127.0.0.5" ,"port": 8004, "instId": 5}
sim6 = {"name": "sim-mme-enb", "ip": "127.0.0.6" ,"port": 8005, "instId": 6}
sim7 = {"name": "sim-mme-enb", "ip": "127.0.0.7" ,"port": 8006, "instId": 7}
sim8 = {"name": "sim-mme-enb", "ip": "127.0.0.8" ,"port": 8007, "instId": 8}
sim9 = {"name": "sim-mme-enb", "ip": "127.0.0.9" ,"port": 8008, "instId": 9}
sim10 = {"name": "sim-mme-enb", "ip": "127.0.0.10" ,"port": 8009, "instId": 10}
sim11 = {"name": "sim-mme-enb", "ip": "127.0.0.11" ,"port": 8010, "instId": 11}
sim12 = {"name": "sim-mme-enb", "ip": "127.0.0.12" ,"port": 8011, "instId": 12}
sim13 = {"name": "sim-mme-enb", "ip": "127.0.0.13" ,"port": 8012, "instId": 13}
sim14 = {"name": "sim-mme-enb", "ip": "127.0.0.14" ,"port": 8013, "instId": 14}
sim15 = {"name": "sim-mme-enb", "ip": "127.0.0.15" ,"port": 8014, "instId": 15}
#sim16 = {"name": "sim-mme-enb", "ip": "127.0.0.16" ,"port": 8015, "instId": 16}
#with object bash you can do any linux cmds eg:
#bash.cmd(["pwd"])





bash_expect = {'cmd': "bash", 'errPattern': r'(Command not found|No such file or directory|Operation not permitted|Permission denied)'}
# bash_expect = {'cmd' : "bash", 'errPattern':r'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}

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
    logger.info("sim: {}".format(sim))
    logger.info("sim_expect: {}".format(sim_expect))
    logger.info("bash: {}".format(bash_expect))
    if kwargs1:
        logger.info("special init itcLibrary {}".format(kwargs1))
        itc.getItcLib(**kwargs1)


def exit2(retv=0):
    itc.close()
    itc_pexpect.close()
    import threading
    active_threads = threading.active_count()
    if active_threads > 1:
        logger.error("Warning there are more threads: {}".format(active_threads))
    exit(retv)
   
    
# start shell and prepare interfaces = execute commads from bash_veth.txt in current directory
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
#    import pdb; pdb.set_trace() 

def start_simulators():
    global mme_console
    global mme_console2
    global mme_console3
    global mme_console4
    global mme_console5
    global mme_console6
    global mme_console7
    global mme_console8
    global mme_console9
    global mme_console10
    global mme_console11
    global mme_console12
    global mme_console13
    global mme_console14
    global mme_console15
#    global mme_console16
  
  
  
    global mme
    global mme2
    global mme3
    global mme4
    global mme5
    global mme6
    global mme7
    global mme8
    global mme9
    global mme10
    global mme11
    global mme12
    global mme13
    global mme14
    global mme15
#    global mme16

    try:
        # import pdb; pdb.set_trace()
        mme_console = itc_pexpect.Itc(sim_expect)
        mme_console2 = itc_pexpect.Itc(sim_expect2)
        mme_console3 = itc_pexpect.Itc(sim_expect3)
        mme_console4 = itc_pexpect.Itc(sim_expect4)
        mme_console5 = itc_pexpect.Itc(sim_expect5)
        mme_console6 = itc_pexpect.Itc(sim_expect6)
        mme_console7 = itc_pexpect.Itc(sim_expect7)
        mme_console8 = itc_pexpect.Itc(sim_expect8)
        mme_console9 = itc_pexpect.Itc(sim_expect9)
        mme_console10 = itc_pexpect.Itc(sim_expect10)
        mme_console11 = itc_pexpect.Itc(sim_expect11)
        mme_console12 = itc_pexpect.Itc(sim_expect12)
        mme_console13 = itc_pexpect.Itc(sim_expect13)
        mme_console14 = itc_pexpect.Itc(sim_expect14)
        mme_console15 = itc_pexpect.Itc(sim_expect15)
#        mme_console16 = itc_pexpect.Itc(sim_expect16)
        
        
        
        mme = itc.Itc(sim)
        mme2 = itc.Itc(sim2)
        mme3 = itc.Itc(sim3)
        mme4 = itc.Itc(sim4)
        mme5 = itc.Itc(sim5)
        mme6 = itc.Itc(sim6)
        mme7 = itc.Itc(sim7)
        mme8 = itc.Itc(sim8)
        mme9 = itc.Itc(sim9)
        mme10 = itc.Itc(sim10)
        mme11 = itc.Itc(sim11)
        mme12 = itc.Itc(sim12)
        mme13 = itc.Itc(sim13)
        mme14 = itc.Itc(sim14)
        mme15 = itc.Itc(sim15)
#        mme16 = itc.Itc(sim16)
        
    
    
    except Exception as e:
        logger.error("Exception from startup : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(3)


    
    

    
'''
###############troubleshooting long answered cmds################
    #import pdb; pdb.set_trace()   
#     import pdb; pdb.set_trace() 
#     try :
#     
# #       mme_console - it starts sim-mme-enb on specified IP and you can put cmds then using mme_console.cmd        
#         mme_console = itc_pexpect.Itc(sim_expect)
#         mme_console2 = itc_pexpect.Itc(sim_expect2)
#         res = mme_console.cmd(["show config","show version"])
#         logger.info("mme_console: %s" % res.data)
#     
# #       Returns object connected to itc channel       
#         mme = itc.Itc(sim)
#         mme2 = itc.Itc(sim2)
#         
#         #enable json ouput
#         mme.cmd(["set json-file stdout"])
#         mme2.cmd(["set json-file stdout"])
#         
#         
#         #res = mme.cmd(["show config"])
#         #logger.info("mme_sim_motherfucker: %s" % res.data)
#         mme.cmd(["show version"])
#         mme2.cmd(["show version"])
#         
#         
# #        mme2.cmd([""show config""])
#         pprint.pprint(mme.cmd(["show version"]))
#         pprint.pprint(mme2.cmd(["show version"]))
# #       pprint.pprint(mme2.cmd(["show config"]))
# #        logger.info("mme.cmd: %s" % res.data)
# #       mme2 = itc.Itc(sim2)
# #       mme.cmd(["set cs server 1 tcp 127.0.0.1 8000"])
#  
# #       start mme itc commands
# #        res = mme.cmd(["show version","show config"])
# #        logger.info(res.data[0])
#         
#     except Exception as e:
#         logger.error("Exception from startup : {}".format(e))
#           
#         traceback.print_tb(e.__traceback__)
#         exit2(2)

'''

    
#######################################################################################
#TEST MORE THAN ONE SIMS
def test():
    logger.info("TEST START")
#    import pdb; pdb.set_trace() 
    
    
#       enable json ouput
    mme.cmd(["set json-file stdout"])
    mme2.cmd(["set json-file stdout"])
    mme3.cmd(["set json-file stdout"])
    mme4.cmd(["set json-file stdout"])
    mme5.cmd(["set json-file stdout"])
    mme6.cmd(["set json-file stdout"])
    mme7.cmd(["set json-file stdout"])
    mme8.cmd(["set json-file stdout"])
    mme9.cmd(["set json-file stdout"])
    mme10.cmd(["set json-file stdout"])
    mme11.cmd(["set json-file stdout"])
    mme12.cmd(["set json-file stdout"])
    mme13.cmd(["set json-file stdout"])
    mme14.cmd(["set json-file stdout"])
    mme15.cmd(["set json-file stdout"])
    
    
    
    try:
        res1 = mme.cmd(["show config","show log-level"])
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res2 = mme2.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res3 = mme3.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res4 = mme4.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res5 = mme5.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res6 = mme.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res7 = mme7.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
            
        res8 = mme8.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res9 = mme9.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res10 = mme10.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res11 = mme11.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res12 = mme12.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res13 = mme13.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res14 = mme14.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
            
        res15 = mme15.cmd(["show version","show log-level"])     
        pprint.pprint(res1.data[0])
        pprint.pprint(res1.data[1])
       
    
        sims = list()
        sims.append(res1)
        sims.append(res2)
        sims.append(res3)
        sims.append(res4)
        sims.append(res5)
        sims.append(res6)
        sims.append(res7)
        sims.append(res8)
        sims.append(res9)
        sims.append(res10)
        sims.append(res11)
        sims.append(res12)
        sims.append(res13)
        sims.append(res14)
        sims.append(res15)
        

        pprint.pprint (len(sims))   
        
#      
    except Exception as e:
        logger.error("Exception from startup : {}".format(e))
     
        traceback.print_tb(e.__traceback__)



    try:
        res = mme.cmd(["show version", "trigger error", "show log-level"])
        logger.info(res)
        logger.error("ERROR: trigger error did not triggered exception !!!")
    except Exception as e:
        logger.error("I have exception which is ok now as we are testing if 'trigger error' command triggers exception Exception {}".format(e))
        traceback.print_tb(e.__traceback__)
    
   
    
    
    

#    import pdb; pdb.set_trace()    
    def timeit(fn):
        @wraps(fn)
        def rate(*args, **kwargs):
            start = datetime.datetime.now()
            res = fn(*args, **kwargs)
            end = datetime.datetime.now()
            return (res, (end - start).total_seconds())
        return rate

    @timeit
    def iterationtest1(iterations):
        while iterations >= 0:
            mme.cmd(["show version"])
            iterations -= 1
    
    iterations = 10000
    logger.debug("Iteration test")
    res, time = iterationtest1(iterations)
    logger.debug("End Iteration test, time {}".format(time))
    logger.debug("rate {} iter/s ".format((iterations / time)))
    
    @timeit
    def itertest2(iterations):
        def gen(iterations):
            while iterations > 0:
                yield "show version"
                iterations -= 1
        return(mme.cmd(gen(iterations)))
    
    
    iterations = 20000
    logger.debug("Iteration test2")
    res, time = itertest2(iterations)
    logger.debug("rate {} iter/s".format((iterations / time)))
    logger.debug("End Iteration test2 {} ".format(time))
    logger.debug("{}".format(len(res.data)))
    
    
    
    
    @timeit
    def itertest3(iterations):
        def gen(iterations):
            while iterations > 0:
                yield "show version"
                iterations -= 1
        it = 0
        tasks1 = list()
        tasks2 = list()
        tasks1.append(mme.acmd(gen(iterations)))
        tasks1.append(mme.acmd(gen(iterations)))
        tasks2.append(mme2.acmd(gen(iterations)))
        tasks2.append(mme2.acmd(gen(iterations)))
        tasks2.append(mme2.acmd(gen(iterations)))
        for task in mme.as_completed(tasks1, timeout=5):
            it += len(task.result.data)
            # import pdb; pdb.set_trace()
        # logger.info("Tasks1 completed {}".format(len(tasks1)))
        for task in mme2.as_completed(tasks2):
            it += len(task.result.data)
        # logger.info("Tasks2 completed {}".format(len(tasks2)))
        return(it)
    
    
    iterations = 10000
    logger.debug("Iteration test3")
    res, time = itertest3(iterations)
    logger.debug("rate {} iter/s (iterations {})".format((res / time), res))
    logger.debug("End Iteration test3 {} ".format(time))   
#     res = mme_console.cmd(["show config"])
#     res_0 = mme.cmd(["show version"]).data[0]['ProgramVersion']
    
#     res = res.strip()
#     res_0 = res_0.strip()
#     pprint.pprint(res)
#     pprint.pprint(res_0)
    
#    if (res) == (res_0):
#        logger.info("version is ok")
#     else:
#         logger.error("vresion is not ok")
    
    
    
    import pdb; pdb.set_trace() 
    
    tasks = list()

    # itcmme.set_debug()
    tasks.append(mme.acmd(["show version"]))
    tasks.append(mme.acmd(["show log-level", "show version"]))

    logger.info("Tasks {}".format(tasks))
    print("the length is :",len(tasks))
    pprint.pprint(len(tasks))
#    logger.info("the length is :".format(len(mme.acmd)))   
    
   
        
        
        


#    if len(tasks) == 15:
#        logger.info("maximum sim num opened")
#    else :
#        logger.error("len(tasks)".format(tasks))
    
#    logger.info("Tasks {}".format(tasks))
    
    # add fileHandler
    fh = logging.FileHandler('/tmp/mytestdebug')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    
    
    
    
    
    
    def my_callback(task):
        logger.info("Calling callback on task {}".format(task))
        logger.info("Task {} returned {}".format(task, res))

    # waiting for task as they are being completed
    try:
        for task in mme.as_completed(tasks, timeout=5):
            res = task.result
            logger.info("Task result {}".format(res))
    except itc.Timeout as e:
        logger.error("Timeout {}".format(e))
        # pass
    except Exception as e:
        logger.error("{}".format(e))

    # assign callback to task
    logger.info("Call backs")
    
    
    
#     res5 = mme_console.cmd(["show log-level"]).data[0]['CurrentLevel']
#     res_5 = mme.cmd(["show log-level"]).data[0]['CurrentLevel']
#     pprint.pprint(res5)
#     pprint.pprint(res_5)
    
#     if (res5) == (res_5):
#         logger.info("show log-level is ok")
#     else:
#         logger.error("show log-level is nok")

#     res7 = mme.cmd(["create profile 1"])
    
#     pprint.pprint(res7)
    
    
    
# now get some values from stats result
#
    
  
    
    
    
    
#    rx = [res_x.data[0]['eth1']['Total']['rx-pkt'], res_x.data[0]['eth2']['Total']['rx-pkt']]
#    if 0 in tx:
#        logger.error("test FAILED")
#        raise ValueError("invalid tx {}".format(tx))
#    if 0 in rx:
#        logger.error("test FAILED")
#        raise ValueError("invalid rx {}".format(rx))
#    logger.error("test PASSED")
        
        




if __name__ == "__main__":
    parse_argumets()
    prepare_interfaces()
    start_simulators()
#    connect_sim()
    # run tests
    try:
        test()
    except Exception as e:
        logger.error("Exception from test : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(5)

    exit2(0)
    

        
