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
    sock.send("PONG\n".encode('utf-8'))

def queuemessage(message):
    msg = 'PRIVMSG ' + auth.channel + ' :' + message
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

def sendmessage(message):
    msg = 'PRIVMSG ' + auth.channel + ' :' + message + get_cooldown_bypass_symbol()
    sock.send((msg + '\r\n').encode('utf-8'))

def sendmessagequeue():
    while True:
        time.sleep(1)
        if not messagequeue.empty():
            sock.send((messagequeue.get() + '\r\n').encode('utf-8'))

sendmessagequeuethread = threading.Thread(target = sendmessagequeue)
sendmessagequeuethread.start()

def start():
    defaultdungeon = db(opt.GENERAL).find_one_by_id(0)
    if defaultdungeon == None:
        db(opt.GENERAL).update_one(0, { '$set': schemes.DUNGEON }, upsert=True)
    defaultadmin = db(opt.TAGS).find_one_by_id(auth.defaultadmin)
    if defaultadmin == None:
        db(opt.TAGS).update_one(auth.defaultadmin, {'$set': { 'admin': 1 } }, upsert=True)
    repo = git.Repo(search_parent_directories=True)
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    db(opt.GENERAL).update_one(0, { '$set': { 'commit': sha[0:7] } } )
    sendmessage(messages.startup_message(branch, sha))

def whisper(user, message):
    sendmessage('.w '+ user + ' ' + message)

def checkuserregistered(username, req=None):
    user = db(opt.USERS).find_one_by_id(username)
    sameuser = req == username if req is not None else True

    if sameuser:
        if user:
            return True
        else:
            sendmessage(messages.you_not_registered(username))
    else:
        target = db(opt.USERS).find_one_by_id(req)
        if target:
            return True
        else:
            sendmessage(messages.user_not_registered(username))
    return False

### Admin Commands ###

def resetcd(username):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        for user in db.raw[opt.USERS].find():
            db(opt.USERS).update_one(user['_id'], { '$set': {
                'entered': 0,
                'last_entry': 0,
                'next_entry': 0
            }})
        queuemessage('Cooldowns reset for all users' + emoji.emojize(' :stopwatch:', use_aliases=True))

def restart(username):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        repo = git.Repo(search_parent_directories=True)
        repo.git.reset('--hard')
        repo.remotes.origin.pull()
        os.system('kill %d' % os.getpid())

def usertag(username, target, tag):
    admin = db(opt.TAGS).find_one_by_id(username)
    if admin is not None and admin['admin'] == 1:
        taglist = ['admin', 'moderator']
        user = checkusername(target)
        if user:
            if tag.lower() in taglist:
                db(opt.TAGS).update_one(user, {'$set': {tag.lower(): 1} }, upsert=True)
                queuemessage(user + ' set to ' + tag.capitalize() + emoji.emojize(' :bell:', use_aliases=True))
