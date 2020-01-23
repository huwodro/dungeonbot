import os
import random
import re
import socket
import sys
import threading
import time

import datetime

import requests
import emoji
import git

import auth
import database as opt
import schemes
import messages

db = opt.MongoDatabase

server = 'irc.chat.twitch.tv'
port = 6667

def connect(manual = False):
    global sock
    sock = socket.socket()
    try:
        sock.connect((server, port))
        sock.send(('PASS ' + auth.token + '\r\n').encode('utf-8'))
        sock.send(('NICK ' + auth.nickname + '\r\n').encode('utf-8'))
        sock.send(("CAP REQ :twitch.tv/tags\r\n").encode('utf-8'))
        for channel in db.raw[opt.CHANNELS].find():
            sock.send(('JOIN #' + channel['_id'] + '\r\n').encode('utf-8'))
        sys.stdout.write('SOCKET CONNECTED\n')
        sys.stdout.flush()
    except socket.error as e:
        sys.stderr.write('SOCKET ERROR: ' + str(e.errno) + '\n')
        sys.stderr.flush()
        if not manual:
            time.sleep(auth.reconnect_timer)
        else:
            os._exit(1) # Shuts down script if called from initialization

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
    db(opt.USERS).update_one(username, {'$set': {
        'entered': 0,
        'last_entry': 0,
        'next_entry': 0
    }})

def pong():
    sock.send(('PONG :tmi.twitch.tv\r\n').encode('utf-8'))

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

queuemessage_lock = threading.Lock()

def queuemessage(message, sendto, channel = None):
    queuemessage_lock.acquire()
    if channel == None:
        for channel in db.raw[opt.CHANNELS].find():
            if db(opt.CHANNELS).find_one_by_id(channel['_id'])['online'] == 0:
                db(opt.CHANNELS).update_one(channel['_id'], { '$set': { 'message_queued': 1 } } )
    else:
        db(opt.CHANNELS).update_one(channel, { '$set': { 'message_queued': 1 } } )
    time.sleep(1.25)
    if sendto == 0:
        msg = 'PRIVMSG #' + channel + ' :' + message
        sock.send((msg + '\r\n').encode('utf-8'))
        db(opt.CHANNELS).update_one(channel, { '$set': { 'message_queued': 0 } } )
    else:
        for channel in db.raw[opt.CHANNELS].find():
            if db(opt.CHANNELS).find_one_by_id(channel['_id'])['online'] == 0:
                msg = 'PRIVMSG #' + channel['_id'] + ' :' + message
                sock.send((msg + '\r\n').encode('utf-8'))
                db(opt.CHANNELS).update_one(channel['_id'], { '$set': { 'message_queued': 0 } } )
    queuemessage_lock.release()

def whisper(user, message, channel):
    msg = 'PRIVMSG #' + channel + ' :.w ' + user + ' ' + message
    sock.send((msg + '\r\n').encode('utf-8'))

def gitinfo():
    repo = git.Repo(search_parent_directories=True)
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    for channel in db.raw[opt.CHANNELS].find():
        if db(opt.CHANNELS).find_one_by_id(channel['_id'])['online'] == 0:
            sendmessage(messages.startup_message(branch, sha), channel['_id'])

def start():
    defaultchannel = db(opt.CHANNELS).find_one_by_id(auth.defaultchannel)
    if defaultchannel == None:
        db(opt.CHANNELS).update_one(auth.defaultchannel, { '$set': schemes.CHANNELS }, upsert=True)
    connect(True) # True for initialization
    defaultdungeon = db(opt.GENERAL).find_one_by_id(0)
    if defaultdungeon == None:
        db(opt.GENERAL).update_one(0, { '$set': schemes.DUNGEON }, upsert=True)
    defaultadmin = db(opt.TAGS).find_one_by_id(auth.defaultadmin)
    if defaultadmin == None:
        db(opt.TAGS).update_one(auth.defaultadmin, {'$set': { 'admin': 1 } }, upsert=True)
    gitinfo()

def checkuserregistered(username, channel, req=None):
    user = db(opt.USERS).find_one_by_id(username)
    sameuser = req == username if req is not None else True
    if sameuser:
        if user and user.get('user_level'):
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

def suggest(username, channel, message):
    suggestions = db(opt.SUGGESTIONS).count_documents({})
    if suggestions < 500:
        try:
            id = db(opt.SUGGESTIONS).find_one(sort=[('_id', -1)])['_id']
        except:
            id = 0
        else:
            id += 1
        db(opt.SUGGESTIONS).update_one(id, {'$set': {
            'user': username,
            'suggestion': message
        }}, upsert=True)
        suggestionthread = threading.Thread(target = queuemessage, args=(messages.suggestion_message(username, str(id)), 0, channel))
        suggestionthread.start()

### Admin Commands ###

def dungeontext(mode, message):
    texts = db(opt.TEXT).count_documents({})
    try:
        id = db(opt.TEXT).find_one(sort=[('_id', -1)])['_id']
    except:
        id = 0
    else:
        id += 1
    db(opt.TEXT).update_one(id, {'$set': {
        'mode': mode,
        'text': message
    }}, upsert=True)

def checksuggestion(username, channel, id):
    suggestion = db(opt.SUGGESTIONS).find_one_by_id(id)['suggestion']
    user = db(opt.SUGGESTIONS).find_one_by_id(id)['user']
    whisper(username, messages.check_suggestion(suggestion, user, str(id)), channel)

def removesuggestion(username, channel, id):
    suggestion = db(opt.SUGGESTIONS).find_one_by_id(id)
    if suggestion is not None:
        db(opt.SUGGESTIONS).delete_one(id)
        whisper(username, messages.suggestion_removed(str(id)), channel)
    else:
        whisper(username, messages.remove_suggestion_error, channel)

def joinchannel(currentchannel, channel, global_cooldown, user_cooldown):
    try:
        name = checkusername(channel).lower()
        if name:
            db(opt.CHANNELS).update_one(name, {'$set': {
                'online': 1,
                'cmdusetime': time.time(),
                'global_cooldown': global_cooldown,
                'user_cooldown': user_cooldown,
                'message_queued': 0
            }}, upsert=True)
            db(opt.TAGS).update_one(name, {'$set': { 'moderator': 1 } }, upsert=True)
            sock.send(('JOIN #' + name + '\r\n').encode('utf-8'))
            repo = git.Repo(search_parent_directories=True)
            branch = repo.active_branch.name
            sha = repo.head.object.hexsha
            sendmessage(messages.startup_message(branch, sha), name)
    except AttributeError:
        queuemessage(messages.no_channel_error(channel), 0, currentchannel)

def partchannel(channel):
    channel = db(opt.CHANNELS).find_one_by_id(channel)
    if channel:
        channel = channel['_id']
        partchannelthread = threading.Thread(target = queuemessage, args=(messages.leaving_channel(checkusername(channel)), 0, channel))
        partchannelthread.start()
        db(opt.CHANNELS).delete_one(channel)
        sock.send(('PART #' + channel + '\r\n').encode('utf-8'))

def listchannels(channel):
    joinedchannels = []
    for joinedchannel in db.raw[opt.CHANNELS].find():
        joinedchannels.append(joinedchannel['_id'])
    queuemessage(messages.list_channels(joinedchannels), 0, channel)

def setcooldown(channel, mode, cooldown, currentchannel):
    if db(opt.CHANNELS).find_one_by_id(channel):
        if mode == 'global':
            db(opt.CHANNELS).update_one(channel, { '$set': { 'global_cooldown': cooldown } } )
        elif mode == 'user':
            db(opt.CHANNELS).update_one(channel, { '$set': { 'user_cooldown': cooldown } } )
        else:
            queuemessage(messages.set_cooldown_error, 0, currentchannel)

def runeval(channel, expression):
    try:
        queuemessage(str(eval(expression)), 0, channel)
    except Exception as e:
        queuemessage(messages.error_message(e), 0, channel)

def runexec(channel, code):
    try:
        exec(code)
    except Exception as e:
        queuemessage(messages.error_message(e), 0, channel)

def resetcd(channel):
    for user in db.raw[opt.USERS].find():
        db(opt.USERS).update_one(user['_id'], { '$set': {
            'entered': 0,
            'last_entry': 0,
            'next_entry': 0
        }})
    queuemessage(messages.reset_cooldown, 1)

def restart():
    queuemessage(messages.restart_message, 1)
    repo = git.Repo(search_parent_directories=True)
    repo.git.reset('--hard')
    repo.remotes.origin.pull()
    sock.send(('QUIT\r\n').encode('utf-8'))
    sock.close()
    os._exit(1)

def usertag(channel, target, tag):
    taglist = ['admin', 'moderator']
    user = checkusername(target)
    if user:
        if tag.lower() in taglist:
            db(opt.TAGS).update_one(user, {'$set': {tag.lower(): 1} }, upsert=True)
            queuemessage(messages.tag_message(user, tag), 0, channel)
