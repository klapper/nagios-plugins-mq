#!/usr/bin/python
import getopt
import sys
import pymqi, CMQC, CMQCFC

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3

STATE_STR = {STATE_OK:"OK",STATE_WARNING:"WARNING",STATE_CRITICAL:"CRITICAL",STATE_UNKNOWN:"UNKNOWN"}

def usage():
    print """Usage: rbh_check_mq_oldest_msg_age -H <HostName> -g <QMGRName> -q <QueueName> [-p <PortNumber>] -a <ChannelName> [-w [<warning threshold sec>],[<warning threshold depth>]] [-c [<critical threshold sec>],[<critical threshold depth>]]"""

def show_help():
    usage()
    print """
Checks MQ queue oldest message age, if queue statistics is not available falling back to q inquire to get current queue depth

 -H, --host                Host name
 -g, --qmgr                Queue Manager Name
 -q, --queue               Queue name
 -p, --port-number         port number (default 1414)
 -a, --channel-name        channel name
 -w, --warning             warning threshold
 -c, --critical            critical threshold

example:
Check age AND depth
rbh_check_mq_oldest_msg_age.py -H host1 -g QM1 -q Q1 -a SYSTEM.ADMIN.SVRCONN -w 5,100 -c 10,200
Check only age:
rbh_check_mq_oldest_msg_age.py -H host2 -g QM2 -q SYSTEM.CLUSTER.REPOSITORY.QUEUE -a SYSTEM.ADMIN.SVRCONN -w 1 -c 2
Check only depth:
rbh_check_mq_oldest_msg_age.py -H 127.0.0.1 -g QM3 -q SYSTEM.CLUSTER.REPOSITORY.QUEUE -a SYSTEM.ADMIN.SVRCONN -w ,1 -c ,2


"""

def exit_with_state(exit_code):
    global qmgr
    try:
        qmgr.disconnect()
    except:
        pass
    del qmgr
    sys.exit(exit_code)


def convert_to_int(a):
    try:
        ret = int(a)
    except ValueError:
        ret = None
    return ret

def none_to_empty(a):
    if a:
        return a
    else:
        return ''

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hH:g:q:p:a:w:c:", ["help", "host=","qmgr=","queue=","port=","channel-name=","warning=","critical="])
    except getopt.GetoptError, err:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    hostName = None
    qmgrName = None
    queueName = None
    portNumber = 1414
    channelName = None
    warning_sec = None
    warning_depth = None
    critical_sec = None
    critical_depth = None
    for o, a in opts:
        if o in ("-h", "--help"):
            show_help()
            sys.exit()
        elif o in ("-H", "--host"):
            hostName = a
        elif o in ("-g", "--qmgr"):
            qmgrName = a
        elif o in ("-q", "--queue"):
            queueName = a            
        elif o in ("-p", "--port"):
            portNumber = convert_to_int(a)
        elif o in ("-a", "--channel-name"):
            channelName = a
        elif o in ("-w", "--warning"):
            p = a.partition(',')
            if p[0]:
                warning_sec = convert_to_int(p[0])
            if p[2]:
                warning_depth = convert_to_int(p[2])
        elif o in ("-c", "--critical"):
            p = a.partition(',')
            if p[0]:
                critical_sec = convert_to_int(p[0])
            if p[2]:
                critical_depth  = convert_to_int(p[2])

        else:
            assert False, "unhandled option"
#    print "hostname:%s,q:%s,p:%s,channel:%s,w:%s,c:%s,m:%s,limit:%s" % (hostName,queueName,portNumber,channelName,warningTreshold,criticalTreshold,browseMessages,limitMessageSize)
    if not (hostName and portNumber and queueName and qmgrName and channelName and ((warning_sec and critical_sec) or (warning_depth and critical_depth))):
        usage()
        sys.exit(2)
    conn_info="%s(%s)" % (hostName,portNumber)
    global qmgr
    try:
        qmgr = pymqi.connect(qmgrName,channelName,conn_info)
    except pymqi.MQMIError, e:
        print "UNKNOWN - unable to connect to Qmanager, reason: %s" % (e)
        exit_with_state(STATE_UNKNOWN)

    try:
        pcf = pymqi.PCFExecute(qmgr)
        stats = pcf.MQCMD_INQUIRE_Q_STATUS({CMQC.MQCA_Q_NAME: queueName})
    except pymqi.MQMIError, e:
        print "UNKNOWN - Can not get status information for queue:%s, reason: %s" % (queueName,e)
        exit_with_state(STATE_UNKNOWN)

    q_depth = stats[0][CMQC.MQIA_CURRENT_Q_DEPTH]
    oldest_msg_age = stats[0][CMQCFC.MQIACF_OLDEST_MSG_AGE]
    if oldest_msg_age == -1: #NOT available queue level monitoring is off
        # fall back to q inquire
        try:
            q = pymqi.Queue(qmgr,queueName,CMQC.MQOO_BROWSE | CMQC.MQOO_INQUIRE)
        except pymqi.MQMIError, e:
            print "UNKNOWN - unable to open %s, reason: %s" % (queueName,e)
            exit_with_state(STATE_UNKNOWN)
        try:
            q_depth = q.inquire(CMQC.MQIA_CURRENT_Q_DEPTH)
        except pymqi.MQMIError, e:
            print "UNKNOWN - unable to inquire %s depth" % (queueName)
            exit_with_state(STATE_UNKNOWN)
    if ((critical_sec) and not (critical_sec == -1) and (oldest_msg_age > critical_sec)) or (((oldest_msg_age == -1) or (critical_sec == -1))and (critical_depth) and (q_depth >= critical_depth)):
            exit_state = STATE_CRITICAL
    elif ((warning_sec) and not (warning_sec == -1) and (oldest_msg_age > warning_sec)) or (((oldest_msg_age == -1) or (warning_sec == -1)) and (warning_depth) and (q_depth >= warning_depth)):
            exit_state = STATE_WARNING
    else:
        exit_state = STATE_OK
    msg = ''
    perf = '' 
    if oldest_msg_age > 0:
        d = divmod(oldest_msg_age,60*60*24)
        h = divmod(d[1],60*60)
        m = divmod(h[1],60)
        msg = "oldest message age is: %dday, %02dhour, %02dmin, %02dsec" % (d[0],h[0],m[0],m[1])
        perf = "'%s'=%ss;%s;%s;0;;" % ("Oldest MSG age",oldest_msg_age,none_to_empty(warning_sec),none_to_empty(critical_sec))
    if msg:
        msg = msg + ", "
    msg = msg + "current queue depth: %s" % (q_depth)
    perf = perf + "'%s'=%s;%s;%s;0;;" % ("Queue depth",q_depth,none_to_empty(warning_depth),none_to_empty(critical_depth))
    print("%s - %s %s |%s" % (STATE_STR[exit_state],queueName,msg,perf))
    exit_with_state(exit_state)



if __name__ == "__main__":
    main()


