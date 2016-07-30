import config
import datetime
import requests
import json
import iso8601
import smtplib
import base64
from dateutil import tz
from unidecode import unidecode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

token = config.token
auth = "Bearer %s" % token
#room = config.roomid
ignorelist = config.ignorelist
date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
headers = {
    'authorization': auth,
    'cache-control': "no-cache",
    'content-type': 'application/json'
    }

def getMessages(room):
    url = "https://api.ciscospark.com/v1/messages"
    querystring = {"roomId": room}

    response = requests.request("GET", url, headers=headers, params=querystring)
    messages = json.loads(response.content)
    messages = messages[u'items']

    return messages

def todayMessage():
    messages = getMessages()
    todaymsg_list = []
    for message in messages:
        msgdate = message[u'created']
        msgdate = iso8601.parse_date(msgdate).date()
        if date == msgdate:
            #print message[u'personEmail'], ": ", message[u'text']
            todaymsg_list.append(message)
    return todaymsg_list

def createEmailBody(msg_list):
    body = "Here is what you missed yesterday, %s-%s-%s:\n" % (date.month, date.day, date.year)
    for message in reversed(msg_list):
        #body = body , str(message[u'personEmail']), ": ", str(message[u'text']), "\n"
        #msgtime = str(iso8601.parse_date(message[u'created']).time().hour) + ":" +\
        #          str(iso8601.parse_date(message[u'created']).time().minute) + ":" + \
        #          str(iso8601.parse_date(message[u'created']).time().second)
        msgtime = iso8601.parse_date(message[u'created']).strftime("%I:%M:%S%p")
        #body = body + "%s - %s:  \n" % (str(msgtime), str(message[u'personEmail']))
        body = body + "%s - %s: %s \n" % (str(msgtime), str(message[u'displayName']),
                                          message[u'text'])
    body = body.encode('utf-8').strip()
    return body

def getUsers():
    url = "https://api.ciscospark.com/v1/memberships"
    querystring = {"roomId": room}

    response = requests.request("GET", url, headers=headers, params=querystring)
    users = json.loads(response.content)
    users = users[u'items']
    user_list = []
    for user in users:
        ##Ignore monitor bots
        if user[u'isMonitor'] == False:
            user_list.append(str(user['personEmail']))
    return user_list

def getDisplayName(personId):
    url = "https://api.ciscospark.com/v1/people/" + personId

    response = requests.request("GET", url, headers=headers)
    userinfo = json.loads(response.content)
    displayName = str(userinfo[u'displayName'])

    return displayName

def getRoomList():
#	roominfo = {u'items': [{u'created': u'2015-11-30T20:46:32.867Z', u'title': u'Thoughts in the Clouds', u'isLocked': False, u'lastActivity': u'2016-07-28T22:04:24.688Z', u'type': u'group', u'id': u'Y2lzY29zcGFyazovL3VzL1JPT00vNzA5MGNmMzAtOTdhMy0xMWU1LWIyNzAtZDM2ZWRmMzJlODMz'}]}
	url = "https://api.ciscospark.com/v1/rooms"
	
	response = requests.request("GET", url, headers=headers)
	roominfo = json.loads(response.content.decode('utf8'))
	rooms = roominfo[u'items']

	return rooms

def iterateRooms(rooms):
	for room in rooms:
		rid = str(room[u'id'])
		rpkid = str(base64.b64decode(rid))
		arr_rpkid = rpkid.split("/")
		#print(arr_rpkid)
		rpkid = arr_rpkid[-1]
		rpkid = rpkid[:-1]								#in python3, there is an extra '
		#print(rid,rpkid)
		participants = getParticipantList(rpkid)
		iterateParticipants(participants,rpkid)
	return 0

def getParticipantList(roompkid):
	url = "https://conv-a.wbx2.com/conversation/api/v1/conversations/" + roompkid + "?uuidEntryFormat=true&personRefresh=true&latestActivity=&participantAckFilter=all&activitiesLimit=30&ackFilter=noack"

	response = requests.request("GET", url, headers=headers)
	convoinfo = json.loads(response.content.decode('utf8'))
	participants = convoinfo[u'participants'][u'items']

	return participants

def iterateParticipants(participants,roomid):
	for participant in participants:
		pt = participant[u'type']
		if pt == "PERSON":
			pe = participant[u'emailAddress']
			if "roomProperties" in participant:
				pm = participant[u'roomProperties'][u'lastSeenActivityUUID']
				pu = bytes("ciscospark://us/MESSAGE/" + pm, "ascii")
				pi = base64.b64encode(pu).decode("ascii")
				arrm = findMessageInRoom(roomid,pi)
			
				processParticipantAction(pi,pe,arrm)
	
	return 0

def getDisplayName(userid):
	url = "https://api.ciscospark.com/v1/people/" + userid

	response = requests.request("GET", url, headers=headers)
	userinfo = json.loads(response.content.decode('utf8'))
	pd = userinfo[u'displayName']
	
	return pd

def findMessageInRoom(roomid,messageid):
	url = "https://api.ciscospark.com/v1/messages?roomId=" + roomid + "&max=100"

	response = requests.request("GET", url, headers=headers)
	msginfo = json.loads(response.content.decode('utf8'))
	messages = msginfo[u'items']

	ucache = {}
	mcount = 0
	mcache = {}
	for message in messages:
		mi = str(message[u'id'])
		mt = unidecode(message[u'text'])
		mc = str(message[u'created'])
		mfi = str(message[u'personId'])
		mfe = str(message[u'personEmail'])
		mfd = mfe
		if mfi in ucache:
			mfd = ucache[mfi]
		else:
			mfd = str(getDisplayName(mfi))
			ucache[mfi] = mfd

		if mi == messageid:
			return mcache
		else:
			mcache[mcount] = {"id": mi, "text": mt, "created": mc, "personEmail": mfe, "displayName": mfd}
			mcount = mcount + 1
			
	return 0

def processParticipantAction(partid, partemail, unreadmessages):
	from_zone = tz.gettz('UTC')
	to_zone = tz.gettz('America/Chicago')

	#print(partemail,"::",partid)
	#print("::",unreadmessages,"::")
	#print(type(unreadmessages))

	body = ""
	if len(unreadmessages) > 0:
		todaymsg_list = []
		for messagenum in unreadmessages:
			#print("Num=",messagenum)
			#print("1")
			message = unreadmessages[messagenum]
			#print("2")
			if 'created' in message:
				msgdate = message.get('created')			#['created']
				msgdate = str(iso8601.parse_date(msgdate))
				arr_date = msgdate.split(".")
				msgdate = arr_date[0]
				#print(msgdate)
				t = datetime.datetime.strptime(msgdate, '%Y-%m-%d %H:%M:%S')
				t = t.replace(tzinfo=from_zone)
				t = t.astimezone(to_zone)
				message['created'] = str(t)
				msgdate = t.date()
	        	#print("2.4")
	        	#print("Date2=",msgdate)
	        	#print("2.5")
				if date == msgdate:
					todaymsg_list.append(message)

        	#print("3")

			#print(type(message))
			#print("Msg=",message)
			#if "created" in message:
			#	print("found it")
        	#print("Date2=",msgdate)
        	#if date == msgdate:
			#	todaymsg_list.append(message)
		body = createEmailBody(todaymsg_list).decode("ascii")

	if body == "":
		print(partemail + ": no message")
	else:
		print(partemail + ": message")
		sendEmailMessage(partemail, body)

	#print("------------------------------------------\n")

def sendEmailMessage(msgto, msgbody):
	sender = config.sender
	server = config.server
	server_port = config.server_port

	msg = MIMEMultipart()
	body = MIMEText(msgbody)

	msg['Subject'] = "Daily Summary"
	msg['From'] = sender
	msg['To'] = msgto
	msg.attach(body)

	#print msg

	smtpObj = smtplib.SMTP(server, server_port)
	smtpObj.sendmail(msg["From"], msg["To"].split(","), msg.as_string())

iterateRooms(getRoomList())
#print(rooms)

