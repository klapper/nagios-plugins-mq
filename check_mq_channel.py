#!/usr/bin/python
import getopt
import sys
import pymqi, CMQC, CMQCFC

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3


def usage():
    print """Usage: rbh_check_mq_channel_status -H <HostName> -g <QMGRName> -p <PortNumber> -a <ChannelName for connection> -t <ChannelName for test>"""

def show_help():
    usage()
    print """
Checks MQ channel status

 -H, --host                Host name
 -g, --qmgr                Queue Manager Name
 -p, --port-number         port number (default 1414)
 -a, --channel-name-conn   channel name for connection
 -t, --channel-name        channel name for test

example:
rbh_check_mq_channel_status.py -H host1 -g QM1 -a SYSTEM.ADMIN.SVRCONN -t nameofthechannel

"""

def exit_with_state(exit_code):
    global qmgr
    try:
        qmgr.disconnect()
    except:
        pass
    sys.exit(exit_code)
    
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hH:g:p:a:t:", ["help", "host","qmgr=","port=","channel-name=","channel-name-conn="])
    except getopt.GetoptError, err:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    hostName=None
    qmgrName=None
    portNumber=1414
    channelNameConn=None
    channelNameTest=None
    for o, a in opts:
        if o in ("-h", "--help"):
            show_help()
            sys.exit()
        elif o in ("-H", "--host"):
            hostName = a
        elif o in ("-g", "--qmgr"):
            qmgrName = a
        elif o in ("-p", "--port"):
            portNumber = int(a)
        elif o in ("-a", "--channel-name-conn"):
            channelNameConn = a
        elif o in ("-t", "--channel-name"):
            channelNameTest = a
        else:
            assert False, "unhandled option"
    if not (hostName and portNumber and channelNameTest and qmgrName and channelNameConn):
        usage()
        exit_with_state(STATE_UNKNOWN)
#    if len(channelNameConn) > MQ_CHANNEL_NAME_LENGTH:
#        print "UNKNOWN - Channel name are too long."
    conn_info="%s(%s)" % (hostName,portNumber)
    global qmgr
    try:
        qmgr = pymqi.connect(qmgrName,channelNameConn,conn_info)
    except pymqi.MQMIError, e:
        print "UNKNOWN - unable to connect to Qmanager, reason: %s" % (e)
        exit_with_state(STATE_UNKNOWN)
    channel_name = ''
    try:
        pcf = pymqi.PCFExecute(qmgr)
        channel_names = pcf.MQCMD_INQUIRE_CHANNEL({CMQCFC.MQCACH_CHANNEL_NAME: channelNameTest})
        if channel_names[0]:
            channel_name = channel_names[0][CMQCFC.MQCACH_CHANNEL_NAME].rstrip()
            channel_type = channel_names[0][CMQCFC.MQIACH_CHANNEL_TYPE]
        else:
            print("CRITICAL - Channel %s does not exists." % (channelNameTest))
            exit_with_state(STATE_UNKNOWN)
    except pymqi.MQMIError,e :
        print("UNKNOWN - Can not list MQ channels. reason: %s" % (e))
        exit_with_state(STATE_UNKNOWN)
    status_available = True
    try:
        attrs = "MQCACH_CHANNEL_NAME MQIACH_BYTES_RCVD MQIACH_BYTES_SENT"
        pcf = pymqi.PCFExecute(qmgr)
        channels = pcf.MQCMD_INQUIRE_CHANNEL_STATUS({CMQCFC.MQCACH_CHANNEL_NAME: channelNameTest})
    except pymqi.MQMIError, e:
        if e.comp == CMQC.MQCC_FAILED and e.reason == CMQCFC.MQRCCF_CHL_STATUS_NOT_FOUND:
            status_available = False
            pass
        else:
            print "UNKNOWN - Can not get status information, reason: %s" % (e)
            exit_with_state(STATE_UNKNOWN)

    infomsg = {CMQCFC.MQCHS_INACTIVE:"Channel is inactive",
               CMQCFC.MQCHS_BINDING:"Channel is negotiating with the partner.",
               CMQCFC.MQCHS_STARTING:"Channel is waiting to become active.",
               CMQCFC.MQCHS_RUNNING:"Channel is transferring or waiting for messages.",
               CMQCFC.MQCHS_PAUSED:"Channel is paused.",
               CMQCFC.MQCHS_STOPPING:"Channel is in process of stopping.",
               CMQCFC.MQCHS_RETRYING:"Channel is reattempting to establish connection.",
               CMQCFC.MQCHS_STOPPED:"Channel is stopped.",
               CMQCFC.MQCHS_REQUESTING:"Requester channel is requesting connection.",
               CMQCFC.MQCHS_INITIALIZING:"Channel is initializing."}
               
    if status_available:
        status = channels[0][CMQCFC.MQIACH_CHANNEL_STATUS]
        msg = "Channel: %s state is %s (%s)" % (channel_name,status,infomsg[status])
        if (status == CMQCFC.MQCHS_RUNNING or 
           (status == CMQCFC.MQCHS_INACTIVE and not channel_type in (CMQC.MQCHT_REQUESTER,CMQC.MQCHT_CLUSSDR))):
            print("OK - %s" % (msg))
            exit_with_state(STATE_OK)
        if status in (CMQCFC.MQCHS_PAUSED,CMQCFC.MQCHS_STOPPED):
            print("CRITICAL - %s" % (msg))
            exit_with_state(STATE_CRITICAL)
        else:
            print("WARNING - %s" % (msg))
            exit_with_state(STATE_WARNING)
    else:
        if channel_type in (CMQC.MQCHT_REQUESTER,CMQC.MQCHT_CLUSSDR):
            print("CRITICAL - Channel %s is defined, but status is not available. As this channel is defined as CLUSDR or REQUESTER type channel, therefore it should be running." % (channelNameTest))
            exit_with_state(STATE_CRITICAL)
        else:
            print("OK - Channel %s is defined, but status is not available. This may indicate that the channel has not been used." % (channelNameTest))
            exit_with_state(STATE_OK)


if __name__ == "__main__":
    main()


