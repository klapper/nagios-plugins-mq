#!/usr/bin/python 
import getopt
import pymqi, CMQC, CMQCFC, CMQXC
import sys

def usage():
    print """Usage: list_mq_channels.py -H <hostName> -g <qmgrName> -a <channelName> [-p <portNumber>] [-t <channelType>]"""

def help():
    usage()
    print """
List MQ channels

 -H, --host                Host name
 -g, --qmgr                Queue Manager Name
 -p, --port-number         port number (default 1414)
 -a, --channel-name        Channel name
 -t, --channel-type        Channel types filter (default: all)

Valid channel types are:
  all                      All channel types
  sender                   Sender
  server                   Server
  receiver                 Receiver
  requester                Requester
  svrconn                  Server-connection (for use by clients)
  clntconn                 Client connection
  clussdr                  Cluster-sender

example:
list_mq_channels.py -H host1 -g QM1 -a SYSTEM.ADMIN.SVRCONN
list_mq_channels.py -H 127.0.0.1 -g QM1 -a SYSTEM.ADMIN.SVRCONN -t svrconn

""" 

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hH:g:p:a:t:", ["help", "host=","qmgrName=","port=","channel=","channel-type="])
    except getopt.GetoptError, err:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(-1)
    hostName = None
    qmgrName = None
    portNumber = 1414
    channelName = None
    channelTypeName = "all"
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
        elif o in ("-t", "--channel-type"):
            channelTypeName = a
        else:
            assert False, "unhandled option"
    if ((not (hostName and portNumber and channelName and qmgrName)) and
      (channelTypeName not in ["all","sender","server","receiver","requester","svrconn","clntconn","clussdr"])):
        sys.stderr.write("Wrong Parameters.\n")
        usage()
        sys.exit(-1)
    if channelTypeName == "all":
        channel_type = CMQC.MQCHT_ALL
    elif channelTypeName == "sender":
        channel_type = CMQC.MQCHT_SENDER
    elif channelTypeName == "server":
        channel_type = CMQC.MQCHT_SERVER
    elif channelTypeName == "receiver":
        channel_type = CMQC.MQCHT_RECEIVER
    elif channelTypeName == "requester":
        channel_type = CMQC.MQCHT_REQUESTER
    elif channelTypeName == "svrconn":
        channel_type = CMQC.MQCHT_SVRCONN
    elif channelTypeName == "clntconn":
        channel_type = CMQC.MQCHT_CLNTCONN
    elif channelTypeName == "clussdr":
        channel_type = CMQC.MQCHT_CLUSSDR
    else:
        channel_type = CMQC.MQCHT_ALL
 
    qmgr = None 
    try: 
        qmgr = pymqi.connect(qmgrName,channelName,"%s(%s)" % (hostName,portNumber))
        pcf = pymqi.PCFExecute(qmgr)
    
        response = pcf.MQCMD_INQUIRE_CHANNEL_NAMES({CMQCFC.MQCACH_CHANNEL_NAME:"*",CMQCFC.MQIACH_CHANNEL_TYPE:channel_type})
        for channels in response:
            for channel in channels[CMQCFC.MQCACH_CHANNEL_NAMES]:
                print(channel)
    except pymqi.MQMIError, e:
        sys.stderr.write("Error on executing PCF command: INQUIRE_CHANNEL_NAMES, reason: %s\n" % (e))
        sys.exit(e.reason)
    try:
        if qmgr:
            qmgr.disconnect()
    except pymqi.MQMIError, e:
        pass

if __name__ == "__main__":
    main()
