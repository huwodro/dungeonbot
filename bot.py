import auth
import commands as cmd
import db
import emoji
import re
import requests
import socket
import threading
import time
import utility as util

floodcounter = 0

server = 'irc.chat.twitch.tv'
port = 6667

sock = socket.socket()
sock.connect((server, port))
sock.send(('PASS ' + auth.token + '\r\n').encode('utf-8'))
sock.send(('NICK ' + auth.nickname + '\r\n').encode('utf-8'))
sock.send(('JOIN ' + auth.channel + '\r\n').encode('utf-8'))
sock.send(("CAP REQ :twitch.tv/tags\r\n").encode('utf-8'))

def floodprotection():
    global floodcounter
    while True:
        if floodcounter > 0:
            time.sleep(3)
            floodcounter = 0

floodprotectionthread = threading.Thread(target = floodprotection)
floodprotectionthread.start()

def livecheck():
    while True:
        headers = { 'Client-ID': auth.clientID }
        params = (('user_login', auth.channeluser),)
        response = requests.get('https://api.twitch.tv/helix/streams', headers=headers, params=params).json()
        if not response['data']:
            db.generalcollection.update_one( {'_id': 0}, {'$set': {'open': 1} } )
        else:
            db.generalcollection.update_one( {'_id': 0}, {'$set': {'open': 0} } )
        time.sleep(5)

livecheckthread = threading.Thread(target = livecheck)
livecheckthread.start()

def sendmessagequeue():
    while True:
        time.sleep(1.25)
        sock.send((util.messagequeue.get() + '\r\n').encode('utf-8'))

sendmessagequeuethread = threading.Thread(target = sendmessagequeue)
sendmessagequeuethread.start()

def sendmessage(message):
    global floodcounter
    if floodcounter == 0 and util.messagequeue.empty():
        if type(message) is str:
            msg = 'PRIVMSG ' + auth.channel + ' :' + message
            sock.send((msg + '\r\n').encode('utf-8'))
            floodcounter += 1

def whisper(user, message):
    sendmessage('.w '+ user + ' ' + message)

sendmessage(util.start())

while True:
    resp = emoji.demojize(sock.recv(2048).decode('utf-8'))

    if resp.startswith('PING'):
        sock.send("PONG\n".encode('utf-8'))

    elif len(resp) > 0:
        username = re.search('display-name=(.+?);', resp)
        if username:
            username = username.group(1)
        message = re.search(':(.*)\s:(.*)', resp)
        if message:
            message = message.group(2).strip()

            if db.generalcollection.find_one( {'_id': 0} )['open'] == 1:
                if floodcounter == 0:

                    if (message == '+commands' or message == '+help'):
                        sendmessage(cmd.commands())

                    if message.startswith('+enterdungeon'):
                        sendmessage(cmd.enterdungeon(username, message))

                    if (message == '+dungeonlvl' or message == '+dungeonlevel'):
                        sendmessage(cmd.dungeonlvl())

                    if message == '+dungeonmaster':
                        sendmessage(cmd.dungeonmaster())

                    if message == '+dungeonstats':
                        sendmessage(cmd.dungeonstats())

                    if message == '+dungeonstatus':
                        sendmessage(cmd.dungeonstatus())

                    if (message == '!ping' or message == '+ping'):
                        sendmessage(cmd.ping())

                    if message == '+register':
                        sendmessage(cmd.register(username))

                    if (message.startswith('+xp') or message.startswith('+exp')):
                        sendmessage(cmd.userexperience(username, message))

                    if (message.startswith('+lvl') or message.startswith('+level')):
                        sendmessage(cmd.userlevel(username, message))

                    if message.startswith('+winrate'):
                        sendmessage(cmd.winrate(username, message))

            if message.startswith('+tag'):
                util.usertag(username, message)

            if message == '+resetcd':
                util.resetcd(username)

            if message == '+restart':
                util.restart(username)
