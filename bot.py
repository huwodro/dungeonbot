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

            if (message == '!ping' or message == '+ping') and floodcounter == 0:
                sendmessage(cmd.ping())

            if (message == '+commands' or message == '+help') and floodcounter == 0:
                sendmessage(cmd.commands())

            if message == '+register' and floodcounter == 0:
                sendmessage(cmd.register(username))

            if (message == '+dungeonlvl' or message == '+dungeonlevel') and floodcounter == 0:
                sendmessage(cmd.dungeonlvl())

            if (message.startswith('+xp') or message.startswith('+exp')) and floodcounter == 0:
                sendmessage(cmd.userexperience(username, message))

            if (message.startswith('+lvl') or message.startswith('+level')) and floodcounter == 0:
                sendmessage(cmd.userlevel(username, message))

            if message.startswith('+winrate') and floodcounter == 0:
                sendmessage(cmd.winrate(username, message))

            if message.startswith('+enterdungeon') and floodcounter == 0:
                sendmessage(cmd.enterdungeon(username, message))

            if message == '+dungeonmaster' and floodcounter == 0:
                sendmessage(cmd.dungeonmaster())

            if message == '+dungeonstats' and floodcounter == 0:
                sendmessage(cmd.dungeonstats())

            if message == '+dungeonstatus' and floodcounter == 0:
                sendmessage(cmd.dungeonstatus())

            if message.startswith('+tag'):
                util.usertag(username, message)

            if message == '+resetcd':
                util.resetcd(username)

            if message == '+restart':
                util.restart(username)
