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
import subprocess
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

'''Python provides two very important features to handle any unexpected error in your Python programs and to add debugging capabilities in them'''
class ParamError(Exception):  
    def __init__(self, arg):  #exception for errors we expect like file not found e.g
        self.args = arg

logger = logging.getLogger(__name__)
'''gets next system argument'''
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
    
    




def exit2(retv=0):
    itc.close()
    itc_pexpect.close()


def parameters():

    global sim_list
    global sim_expect_list
    
    sim_list =[]
    sim_expect_list=[]
    for i in  range(0, 15):
        srvIp = str(ipaddress.IPv4Address('127.0.0.1')+i)
        sim_list.append({"name": "sim-mme-enb", "ip": srvIp ,"port": 8000+i, "instId": 1+i})


    '''sim bash command and arguments to start sim'''

    for i in range(0, 12):
        sim_expect_list.append({ 'cmd': "/opt/netowl/bin/sim-mme-enb -d {} -t {} --pgw-s5s8-address {} --s5-type-gtp --enb-s1u-address {} --enable-cli --itc-server {}:{} --inst-id {}".format(sim_list[i]["ip"],sim_list[i+1]["ip"],sim_list[i+2]["ip"],sim_list[i+3]["ip"],sim_list[i]["ip"],sim_list[i]["port"],sim_list[i]["instId"]),'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'})
 
    for i in range(12, 15):
 
        srvIp1 = str(ipaddress.IPv4Address(sim_list[i]["ip"])+1)
        srvIp2 = str(ipaddress.IPv4Address(sim_list[i]["ip"])+2)
        srvIp3 = str(ipaddress.IPv4Address(sim_list[i]["ip"])+3)        
        sim_expect_list.append({ 'cmd': "/opt/netowl/bin/sim-mme-enb -d {} -t {} --pgw-s5s8-address {} --s5-type-gtp --enb-s1u-address {} --enable-cli --itc-server {}:{} --inst-id {}".format(sim_list[i]["ip"],srvIp1,srvIp2,srvIp3,sim_list[i]["ip"],sim_list[i]["port"],sim_list[i]["instId"]),'prompt': r"CLI> ", 'errPattern': r'(ERROR:|CLI was expecting:)'})
     
    bash_expect = {'cmd': "bash", 'errPattern': r'(Command not found|No such file or directory|Operation not permitted|Permission denied)'} 

'''prepare interfaces'''    
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

'''starting the sims'''
def start_simulators():
    global sim_list
    global sim_expect_list
    global mme_console_list
    global mme_list
     

    try:
        mme_console_list=[]
        mme_list=[]
        for i in range(0, 15):
            mme_console_list.append(itc_pexpect.Itc(sim_expect_list[i]))
            mme_list.append(itc.Itc(sim_list[i]))

        

    
    except Exception as e:
        logger.error("Exception from startup : {}".format(e))
        traceback.print_tb(e.__traceback__)
       
        exit2(3)

'''start testing max number of sims'''
def test():
    global mme_list
    global sim_list
    logger.info("TEST START")

    
    
    '''set output in json format'''
    
    for i in range(0, 15):
        mme_list[i].cmd(["set json-file stdout"])   
#        mme_console_list[i].cmd(["set json-file stdout"])
       
        
    '''execute 2 commands in each simulator and chek max number of sims'''   
    try:
        
        for i in range(0, 15):
            res = mme_list[i].cmd(["show version","show log-level"])
#            pprint.pprint(res) 
            
            pprint.pprint(len(res))
#            pprint.pprint(len(res2))
            
            if (len(res.data)) == 3:
                logger.error(res)
            else:
                logger.info(res)
        
        
        
        
    except Exception as e:
        logger.error("Exception from startup : {}".format(e))
        
     
        traceback.print_tb(e.__traceback__)
            
    if (len(sim_list)) != 15 :
        logger.error("Num of sims NOK (len(sims)):{}".format((len(sim_list))))
    else:
        logger.info("Total sim num  (len(sims)):{}".format((len(sim_list))))
    '''closing sims'''    
    '''closing 5 sims out of 15'''
    close_5_sims()
    '''closing the remaing 10 sims'''
    close_10_sims()
    '''start again all 15 sims'''
    start_simulators() 
    
    '''send mme commands to check functionality'''
    try:
        
        for i in range(0, 15):
            res = mme_list[i].cmd(["show version","show log-level"])
#            pprint.pprint(res) 
            
            pprint.pprint(len(res))
#            pprint.pprint(len(res2))
            
            if (len(res.data)) == 3:
                logger.error(res)
            else:
                logger.info(res)
    
    except Exception as e:
        logger.error("Exception from startup : {}".format(e))
    
def close_5_sims():

    
    
    try:
        k=0
        for i in range(0, 5):
            k=(k+1)
            mme_list[i].close()
            mme_console_list[i].close()
            logger.debug("close:sim: {}, simlist: {}".format(mme_list, mme_console_list))
        logger.info("total number of closed sims:{}".format(k))  
    except Exception as e:
        logger.error("Exception from startup : {}".format(e))    
    


def close_10_sims():

    try:
        k=0

        for i in range(5, 15):
            k=(k+1)
            mme_list[i].close()
            mme_console_list[i].close()
            logger.debug("close:sim: {}, simlist: {}".format(mme_list, mme_console_list))
        logger.info("total number of closed sims:{}".format(k))
    except Exception as e:
        logger.error("Exception from startup : {}".format(e))     




bash_expect = {'cmd': "bash", 'errPattern': r'(Command not found|No such file or directory|Operation not permitted|Permission denied)'}
    
    
    
        
'''internal checking method'''

#itc.getItcLib().netowl.pyapi_print_stats()

   
if __name__ == "__main__":

    parameters()
    prepare_interfaces()
    start_simulators() 
   
#    parse_argumets()
    
    
    try:
        test()
    except Exception as e:
        logger.error("Exception from test : {}".format(e))
        traceback.print_tb(e.__traceback__)
        exit2(5)
    logger.info("TEST STOP")    
#    import pdb; pdb.set_trace()
    exit2(0) 
    
    
    
    
    
    

     
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    