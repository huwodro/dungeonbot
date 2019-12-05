import auth
import db
import emoji
import git
import os
import queue
import re
import requests
import socket
import threading
import time

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
    db.usercollection.update_one( {'_id': username}, {'$set': {'entered': 0} } )
    db.usercollection.update_one( {'_id': username}, {'$set': {'enteredTime': 0} } )
    db.usercollection.update_one( {'_id': username}, {'$set': {'dungeonTimeout': 0} } )
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
        floodcounter += 1

def sendmessagequeue():
    while True:
        time.sleep(1.25)
        sock.send((messagequeue.get() + '\r\n').encode('utf-8'))

sendmessagequeuethread = threading.Thread(target = sendmessagequeue)
sendmessagequeuethread.start()

def start():
    # db.generalcollection.update_many( {'_id': 0}, {'$setOnInsert': {'open': 0, 'dungeonlevel': 0, 'total_experience': 0, 'total_dungeons': 0, 'total_wins': 0, 'total_losses': 0} }, upsert=True )
    # db.tagcollection.update_one( {'_id': 'Huwodro'}, {'$setOnInsert': {'admin': 1} }, upsert=True )

    db.generalcollection.update_one( {'_id': 0}, {'$rename': {'dungeonlevel': 'dungeon_level'}})
    db.usercollection.update_many({}, {'$rename': {'userlevel': 'user_level', 'enteredTime': 'last_entry', 'dungeonTimeout': 'next_entry'}})

    repo = git.Repo(search_parent_directories=True)
    repo.git.reset('--hard')
    repo.remotes.origin.pull()
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    sendmessage(emoji.emojize(':arrow_right:', use_aliases=True) + ' Dungeon Bot (' + branch + ', ' + sha[0:7] + ')')

def whisper(user, message):
    sendmessage('.w '+ user + ' ' + message)

### Admin Commands ###

def resetcd(username):
    if db.tagcollection.count_documents({'_id': username}, limit = 1) == 1:
        if db.tagcollection.find_one( {'_id': username} )['admin'] == 1:
            for user in db.usercollection.find():
                db.usercollection.update_one( {'_id': user['_id']}, {'$set': {'entered': 0} } )
                db.usercollection.update_one( {'_id': user['_id']}, {'$set': {'enteredTime': 0} } )
                db.usercollection.update_one( {'_id': user['_id']}, {'$set': {'dungeonTimeout': 0} } )
            queuemessage('Cooldowns reset for all users' + emoji.emojize(' :stopwatch:'))

def restart(username):
    if db.tagcollection.count_documents({'_id': username}, limit = 1) == 1:
        if db.tagcollection.find_one( {'_id': username} )['admin'] == 1:
            os.system('kill %d' % os.getpid())

def usertag(username, message):
    if db.tagcollection.count_documents({'_id': username}, limit = 1) == 1:
        if db.tagcollection.find_one( {'_id': username} )['admin'] == 1:
            target = re.search('tag (.*)', message)
            if target:
                taglist = ['admin', 'moderator']
                target = target.group(1).split()
                if checkusername(target[0]):
                    if target[1]:
                        if target[1].lower() in taglist:
                            db.tagcollection.update_one( {'_id': checkusername(target[0]) }, {'$set': {target[1].lower(): 1} }, upsert=True )
