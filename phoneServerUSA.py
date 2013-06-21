#import error no module named requests

import datetime
import android, time
import pprint
import json
import requests
import sys
import ast

emails = 'elizabethmgin@gmail.com'
POST_LOAD = [{'user' : 'phone', 'pw' : 'Bug0l0b1'}]
GET_LOAD = [{'user' : 'phone', 'pw' : 's3cr3t'}]

print "initiating droid"
droid = android.Android()

# pass list of messages
# return messageDict in json    
def create_Message_Dict(messages):
    messageDict = {}
    messageString = str(messages)
    messageDict["messages"] = messageString
    messageDict["auth"] = str(POST_LOAD)
    print messageDict
    return messageDict

print "checking existing records"

# print str(SMS.select().count()) + " messages saved so far."

print "entering loop..."
while True:
    try:
        print >> sys.stderr, "within try"
        messages = droid.smsGetMessages(True).result
        if messages:
            print >> sys.stderr, "within if"
            droid.smsMarkMessageRead(droid.smsGetMessageIds(True).result,True) # mark those messages as read
            print str(len(messages)) +" new sms messages!"
            messageDict = create_Message_Dict(messages)
            r = requests.post('http://50.116.10.109:80/~ginontherocks/p/marketMessages/sms_received/', params=messageDict)
        else:
            print >> sys.stderr, 'no new messages!'
            r = requests.get('http://50.116.10.109:80/~ginontherocks/p/marketMessages/sms_to_send/')
            message = json.loads(r.text)
            print >> sys.stderr, message
            messageStr = message['messages']
            messageList = ast.literal_eval(messageStr)
            print >> sys.stderr, messageList
            authStr = message['auth']
            authList = ast.literal_eval(authStr)
            print >> sys.stderr, authList
            if type(messageList[0]) == list:
                print >> sys.stderr, 'within messageList for'
                if authList == GET_LOAD:
                    print >> sys.stderr, 'within if authlist'
                    for message in messageList:
                        print >> sys.stderr, 'within for message loop'
                        print message
                        number = '+' + str(message[0])
                        droid.smsSend(str(number),str(message[1]))
                else:
                    print >> sys.stderr, "authlist does not match; might be insecure"
            else:
                print >> sys.stderr, type(messageList[0])
                print >> sys.stderr, messageList[0]
    except:
        print >> sys.stderr, "within except"
        # droid.sendEmail(emails, 'An exception has Occured', str(sys.exc_type) + '[' + str(sys.exc_value) + ']')
        print >> sys.stderr, str(sys.exc_info()[0]) # These write the nature of the error
        print >> sys.stderr, str(sys.exc_info()[1])
    time.sleep(15)




