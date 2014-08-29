#!/usr/bin/python 
import getopt
import pymqi, CMQC, CMQCFC, CMQXC
import sys

def usage():
    print """Usage: list_mq_queues.py -H <hostName> -g <qmgrName> -a <channelName> [-p <portNumber>] [-t <queueType>] [-u <usageType>]"""

def help():
    usage()
    print """
List MQ queues

 -H, --host                Host name
 -g, --qmgr                Queue Manager Name
 -p, --port-number         port number (default 1414)
 -a, --channel-name        channel name
 -t, --queueType           Queue types filter (default: local)
 -d, --definitionType      Queue Definition type (default: predefined)
 -u, --usageType           filter for normal or transmission queues (default: normal)

Valid queue types are:
  all                      All queue types
  local                    Local queues
  alias                    Alias queue definition
  remote                   Local definition of remote queues
  cluster                  Cluster queues
  model                    Model queue definition

Valid queue definition types are:
  all                      All queue types
  predefined               Predefined permanent queue.
  permanent_dynamic        Dynamically defined permanent queue.
  shared_dynamic           Dynamically defined shared queue. This option is available on z/OS only.
  temporary_dynamic        Dynamically defined temporary queue.
  
Valid usage types are:
  all                      All queue usage types
  normal                   Normal usage.
  transmission             Transmission queue.

example:
list_mq_queues.py -H host1 -g QM1 -a SYSTEM.ADMIN.SVRCONN
list_mq_queues.py -H host2 -g QM2 -a SYSTEM.ADMIN.SVRCONN -t remote
list_mq_queues.py -H 127.0.0.1 -g QM3 -a SYSTEM.ADMIN.SVRCONN --usageType=transmission

""" 

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hH:g:p:a:t:d:u:", ["help", "host=","qmgrName=","port=","channel=","queueType=","definitionType=","usageType="])
    except getopt.GetoptError, err:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(-1)
    hostName = None
    qmgrName = None
    portNumber = 1414
    channelName = None
    queueTypeName = "local"
    definitionTypeName = "predefined"
    usageTypeName = "normal"
    for o, a in opts:
        if o in ("-h", "--help"):
            help()
            sys.exit()
        elif o in ("-H", "--host"):
            hostName = a
        elif o in ("-g", "--qmgr"):
            qmgrName = a
        elif o in ("-p", "--port"):
            portNumber = int(a)
        elif o in ("-a", "--channel"):
            channelName = a
        elif o in ("-t", "--queueType"):
            queueTypeName = a
        elif o in ("-d", "--definitionType"):
            definitionTypeName = a
        elif o in ("-u", "--usageType"):
            usageTypeName = a
        else:
            assert False, "unhandled option"
    if ((not (hostName and portNumber and channelName and qmgrName)) or
      (queueTypeName not in ["all","local","alias","remote","cluster","model"]) or
      (definitionTypeName not in ["all","predefined","permanent_dynamic","shared_dynamic","temporary_dynamic"]) or
      (usageTypeName not in ["all","normal","transmission"])):
        sys.stderr.write("Wrong Parameters.\n")
        usage()
        sys.exit(-1)
    
    prefix = "*"
    if queueTypeName == "all":
        queue_type = CMQC.MQQT_ALL
    elif queueTypeName == "local":
        queue_type = CMQC.MQQT_LOCAL
    elif queueTypeName == "alias":
        queue_type = CMQC.MQQT_ALIAS
    elif queueTypeName == "remote":
        queue_type = CMQC.MQQT_REMOTE
    elif queueTypeName == "cluster":
        queue_type = CMQC.MQQT_CLUSTER
    elif queueTypeName == "model":
        queue_type = CMQC.MQQT_MODEL
    args = {CMQC.MQCA_Q_NAME: prefix,
            CMQC.MQIA_Q_TYPE: queue_type,
            CMQCFC.MQIACF_Q_ATTRS: CMQCFC.MQIACF_ALL,}
 
    qmgr = None 
    try: 
        qmgr = pymqi.connect(qmgrName,channelName,"%s(%s)" % (hostName,portNumber))
        pcf = pymqi.PCFExecute(qmgr)
    
        response = pcf.MQCMD_INQUIRE_Q(args)
        for queue in response:
            queue_name = queue[CMQC.MQCA_Q_NAME]
            definition_type = queue.get(CMQC.MQIA_DEFINITION_TYPE,"all")
            usageType = queue.get(CMQC.MQIA_USAGE,"all")
            if (((definitionTypeName == "all") or 
             (definitionTypeName == "predefined" and definition_type == CMQC.MQQDT_PREDEFINED) or
             (definitionTypeName == "permanent_dynamic" and definition_type == CMQC.MQQDT_PERMANENT_DYNAMIC) or
             (definitionTypeName == "shared_dynamic" and definition_type == CMQC.MQQDT_SHARED_DYNAMIC) or
             (definitionTypeName == "temporary_dynamic" and definition_type == CMQC.MQQDT_TEMPORARY_DYNAMIC)) and
             ((usageTypeName == "all") or
             (usageTypeName == "normal" and usageType == CMQC.MQUS_NORMAL) or
             (usageTypeName == "transmission" and usageType == CMQC.MQUS_TRANSMISSION))):
                print(queue_name)
    except pymqi.MQMIError, e:
        sys.stderr.write("Error on executing PCF command: INQUIRE_Q, reason: %s" % (e))
        sys.exit(e.reason)

    try:
        if qmgr:
            qmgr.disconnect()
    except pymqi.MQMIError, e:
        pass

if __name__ == "__main__":
    main()
