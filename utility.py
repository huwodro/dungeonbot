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
import messages

db = opt.MongoDatabase

messagequeue = queue.Queue()
opendungeonlock = threading.Lock()

server = 'irc.chat.twitch.tv'
port = 6667

def connect (manual = False):
    global sock
    sock = socket.socket()
    try:
        sock.connect((server, port))
        sock.send(('PASS ' + auth.token + '\r\n').encode('utf-8'))
        sock.send(('NICK ' + auth.nickname + '\r\n').encode('utf-8'))
        for channel in db.raw[opt.CHANNELS].find():
            sock.send(('JOIN #' + channel['_id'] + '\r\n').encode('utf-8'))
        sock.send(("CAP REQ :twitch.tv/tags\r\n").encode('utf-8'))
        print('Socket connected.')
    except socket.error as err:
        print('Socket error: ' + str(err.errno))
        if not manual:
            time.sleep(auth.reconnect_timer)
        else:
            os._exit(1) # Shuts down script if called from initialization.

def checkusername(user):
    headers = { 'Client-ID': auth.clientID }
    params = (('login', user),)
    response = requests.get('https://api.twitch.tv/helix/users', headers=headers, params=params).json()
    if 'error' in response:
        return
    elif not response['data']:
        return
    elif 'data' in response:
        return response['data'][0]['display_name']
    else:
        return

def opendungeon(username):
    opendungeonlock.acquire()
    db(opt.USERS).update_one(username, {'$set': {
        'entered': 0,
        'last_entry': 0,
        'next_entry': 0
    }})
    opendungeonlock.release()

def pong():
    sock.send(('PONG :tmi.twitch.tv\r\n').encode('utf-8'))

def queuemessage(message, channel):
    msg = 'PRIVMSG #' + channel + ' :' + message
    messagequeue.put(msg)

last_time_symbol = 0
def get_cooldown_bypass_symbol():
    global last_time_symbol
    if last_time_symbol == 0:
        last_time_symbol = 1
        return ''
    else:
        last_time_symbol = 0
        return ' \U000e0000'

def sendmessage(message, channel):
    msg = 'PRIVMSG #' + channel + ' :' + message + get_cooldown_bypass_symbol()
    sock.send((msg + '\r\n').encode('utf-8'))

def sendmessagequeue():
    while True:
        time.sleep(1)
        if not messagequeue.empty():
            sock.send((messagequeue.get() + '\r\n').encode('utf-8'))

sendmessagequeuethread = threading.Thread(target = sendmessagequeue)
sendmessagequeuethread.start()

def gitinfo():
    repo = git.Repo(search_parent_directories=True)
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    for channel in db.raw[opt.CHANNELS].find():
        sendmessage(messages.startup_message(branch, sha), channel['_id'])

def start():
    connect(True) # True for initialization.
    defaultdungeon = db(opt.GENERAL).find_one_by_id(0)
    if defaultdungeon == None:
        db(opt.GENERAL).update_one(0, { '$set': schemes.DUNGEON }, upsert=True)
    defaultadmin = db(opt.TAGS).find_one_by_id(auth.defaultadmin)
    if defaultadmin == None:
        db(opt.TAGS).update_one(auth.defaultadmin, {'$set': { 'admin': 1 } }, upsert=True)
    gitinfo()

# Unused (?)
# def whisper(user, message):
#     sendmessage('.w '+ user + ' ' + message)

def checkuserregistered(username, channel, req=None):
    user = db(opt.USERS).find_one_by_id(username)
    sameuser = req == username if req is not None else True

    if sameuser:
        if user:
            return True
        else:
            sendmessage(messages.you_not_registered(username), channel)
    else:
        target = db(opt.USERS).find_one_by_id(req)
        if target:
            return True
        else:
            sendmessage(messages.user_not_registered(username), channel)
    return False

### Admin Commands ###

def joinchannel(username, currentchannel, channel):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        try:
            name = checkusername(channel).lower()
            if name:
                db(opt.CHANNELS).update_one(name, { '$set': { 'online': 1 } }, upsert=True)
                db(opt.CHANNELS).update_one(name, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                sock.send(('JOIN #' + name + '\r\n').encode('utf-8'))
                repo = git.Repo(search_parent_directories=True)
                branch = repo.active_branch.name
                sha = repo.head.object.hexsha
                sendmessage(messages.startup_message(branch, sha), name)
        except AttributeError:
            queuemessage(messages.join_channel_error(channel), currentchannel)

def partchannel(username, channel):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        channel = db(opt.CHANNELS).find_one_by_id(channel)
        if channel:
            channel = channel['_id']
            sendmessage(messages.leaving_channel(checkusername(channel)), channel)
            db(opt.CHANNELS).delete_one(channel)
            sock.send(('PART #' + channel + '\r\n').encode('utf-8'))

def listchannels(username, channel):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        joinedchannels = []
        for joinedchannel in db.raw[opt.CHANNELS].find():
            joinedchannels.append(joinedchannel['_id'])
        sendmessage(messages.list_channels(joinedchannels), channel)

def runeval(username, channel, expression):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        try:
            queuemessage(str(eval(expression)), channel)
        except Exception as e:
            queuemessage(messages.error_message(e), channel)

def runexec(username, channel, code):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        try:
            exec(code)
        except Exception as e:
            queuemessage(messages.error_message(e), channel)

def resetcd(username, channel):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        for user in db.raw[opt.USERS].find():
            db(opt.USERS).update_one(user['_id'], { '$set': {
                'entered': 0,
                'last_entry': 0,
                'next_entry': 0
            }})
        queuemessage(messages.reset_cooldown(), channel)

def restart(username):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        sendmessage(messages.restart_message(), auth.defaultchannel)
        repo = git.Repo(search_parent_directories=True)
        repo.git.reset('--hard')
        repo.remotes.origin.pull()
        sock.send(('QUIT\r\n').encode('utf-8'))
        sock.close()
        os.system('kill %d' % os.getpid())

def usertag(username, channel, target, tag):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        taglist = ['admin', 'moderator']
        user = checkusername(target)
        if user:
            if tag.lower() in taglist:
                db(opt.TAGS).update_one(user, {'$set': {tag.lower(): 1} }, upsert=True)
                queuemessage(messages.tag_message(user, tag), channel)
