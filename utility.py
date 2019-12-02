import auth
import db
import emoji
import git
import os
import queue
import re
import requests
import threading

messagequeue = queue.Queue()
opendungeonlock = threading.Lock()

def start():
    db.generalcollection.update_many( {'_id': 0}, {'$setOnInsert': {'open': 0, 'dungeonlevel': 0, 'total_experience': 0, 'total_dungeons': 0, 'total_wins': 0, 'total_losses': 0} }, upsert=True )
    db.tagcollection.update_one( {'_id': 'Huwodro'}, {'$setOnInsert': {'admin': 1} }, upsert=True )
    repo = git.Repo(search_parent_directories=True)
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    return emoji.emojize(':arrow_right:', use_aliases=True) + ' Dungeon Bot (' + branch + ', ' + sha[0:7] + ')'

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
    db.usercollection.update_one( {'_id': username}, {'$set': {'entered': 0} } )
    db.usercollection.update_one( {'_id': username}, {'$set': {'enteredTime': 0} } )
    db.usercollection.update_one( {'_id': username}, {'$set': {'dungeonTimeout': 0} } )
    opendungeonlock.release()

def queuemessage(message):
    msg = 'PRIVMSG ' + auth.channel + ' :' + message
    messagequeue.put(msg)

### Admin Commands ###

def resetcd(username):
    if db.tagcollection.find_one( {'_id': username} )['admin'] == 1:
        for user in db.usercollection.find():
            db.usercollection.update_one( {'_id': user['_id']}, {'$set': {'entered': 0} } )
            db.usercollection.update_one( {'_id': user['_id']}, {'$set': {'enteredTime': 0} } )
            db.usercollection.update_one( {'_id': user['_id']}, {'$set': {'dungeonTimeout': 0} } )
        queuemessage('Cooldowns reset for all users' + emoji.emojize(' :stopwatch:'))

def restart(username):
    if db.tagcollection.find_one( {'_id': username} )['admin'] == 1:
        repo = git.Repo(search_parent_directories=True)
        repo.git.reset('--hard')
        repo.remotes.origin.pull()
        os.system('kill %d' % os.getpid())

def usertag(username, message):
    if db.tagcollection.find_one( {'_id': username} )['admin'] == 1:
        target = re.search('tag (.*)', message)
        if target:
            taglist = ['admin', 'moderator']
            target = target.group(1).split()
            if checkusername(target[0]):
                if target[1]:
                    if target[1].lower() in taglist:
                        db.tagcollection.update_one( {'_id': checkusername(target[0]) }, {'$set': {target[1].lower(): 1} }, upsert=True )
