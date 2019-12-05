import os
import queue
import re
import socket
import threading
import time

import requests
import emoji
import git

import auth
import database as opt
import schemes

db = opt.MongoDatabase

floodcounter = 0
messagequeue = queue.Queue()
opendungeonlock = threading.Lock()

server = 'irc.chat.twitch.tv'
port = 6667

sock = socket.socket()
sock.connect((server, port))
sock.send(('PASS ' + auth.token + '\r\n').encode('utf-8'))
sock.send(('NICK ' + auth.nickname + '\r\n').encode('utf-8'))
sock.send(('JOIN ' + auth.channel + '\r\n').encode('utf-8'))
sock.send(("CAP REQ :twitch.tv/tags\r\n").encode('utf-8'))

def checkusername(user):
    headers = { 'Client-ID': auth.clientID }
    params = (('login', user),)
    response = requests.get('https://api.twitch.tv/helix/users', headers=headers, params=params).json()
    if 'error' in response:
        return
    elif not response['data']:
        return
    elif 'data' in response:
        print(response)
        return response['data'][0]['display_name']
    else:
        return

def floodprotection():
    global floodcounter
    while True:
        if floodcounter > 0:
            time.sleep(3)
            floodcounter = 0

floodprotectionthread = threading.Thread(target = floodprotection)
floodprotectionthread.start()

def opendungeon(username):
    opendungeonlock.acquire()
    db(opt.USERS).update_one(username, {'$set': {
        'entered': 0,
        'last_entry': 0,
        'next_entry': 0
    }})
    opendungeonlock.release()

def pong():
    sock.send("PONG\n".encode('utf-8'))

def queuemessage(message):
    msg = 'PRIVMSG ' + auth.channel + ' :' + message
    messagequeue.put(msg)

def sendmessage(message):
    global floodcounter
    if messagequeue.empty():
        msg = 'PRIVMSG ' + auth.channel + ' :' + message
        sock.send((msg + '\r\n').encode('utf-8'))
        print(msg)
        floodcounter += 1

def sendmessagequeue():
    while True:
        time.sleep(1.25)
        sock.send((messagequeue.get() + '\r\n').encode('utf-8'))

sendmessagequeuethread = threading.Thread(target = sendmessagequeue)
sendmessagequeuethread.start()

def start():
    print('Starting...')
    defaultdungeon = db(opt.DUNGEONS).find_one_by_id(0)
    if defaultdungeon == None:
        db(opt.DUNGEONS).update_one(0, { '$set': schemes.DUNGEON }, upsert=True)
    defaultadmin = db(opt.TAGS).find_one_by_id(auth.defaultadmin)
    if defaultadmin == None:
        db(opt.TAGS).update_one(auth.defaultadmin, {'$set': { 'admin': 1 } }, upsert=True)
    # repo = git.Repo(search_parent_directories=True)
    # repo.git.reset('--hard')
    # repo.remotes.origin.pull()
    # branch = repo.active_branch.name
    # sha = repo.head.object.hexsha
    # sendmessage(emoji.emojize(':arrow_right:', use_aliases=True) + ' Dungeon Bot (' + branch + ', ' + sha[0:7] + ')')

def whisper(user, message):
    sendmessage('.w '+ user + ' ' + message)

def checkuserregistered(username, req=None):
    user = db(opt.USERS).find_one_by_id(username)
    if user == None:
        sameuser = req == username if req != None else True
        if sameuser:
            sendmessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True))
        else:
            sendmessage(username + ', that user is not registered!' + emoji.emojize(' :warning:', use_aliases=True))
        return False
    else:
        return True

### Admin Commands ###

def resetcd(username):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin != None and admin['admin'] == 1:
        for user in db.raw[opt.USERS].find():
            db(opt.USERS).update_one(user['_id'], { '$set': {
                'entered': 0,
                'enteredTime': 0,
                'dungeonTimeout': 0
            }})
        queuemessage('Cooldowns reset for all users' + emoji.emojize(' :stopwatch:'))

def restart(username):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin != None and admin['admin'] == 1:
        os.system('kill %d' % os.getpid())

def usertag(username, message):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin != None and admin['admin'] == 1:
        target = re.search('tag (.*)', message)
        if target:
            taglist = ['admin', 'moderator']
            target = target.group(1).split()
            username = checkusername(target[0])
            if username:
                if target[1]:
                    if target[1].lower() in taglist:
                        db(opt.TAGS).update_one(username, {'$set': {target[1].lower(): 1} }, upsert=True)
