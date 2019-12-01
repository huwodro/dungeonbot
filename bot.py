from pymongo import MongoClient
import threading
import datetime
import requests
import socket
import random
import emoji
import queue
import auth
import time
import git
import os
import re

botStart = time.time()
floodCounter = 0
messageQueue = queue.Queue()

client = MongoClient('localhost', 27017)
db = client['Twitch']
generalCollection = db['General']
userCollection = db['UserStats']
tagCollection = db['UserTags']

def init():
    generalCollection.update_many( {'_id': 0}, {'$setOnInsert': {'open': 0, 'dungeonlevel': 0, 'total_experience': 0, 'total_dungeons': 0, 'total_wins': 0, 'total_losses': 0} }, upsert=True )
    tagCollection.update_one( {'_id': 'Huwodro'}, {'$setOnInsert': {'admin': 1} }, upsert=True )

init()

server = 'irc.chat.twitch.tv'
port = 6667

sock = socket.socket()
sock.connect((server, port))
sock.send(('PASS ' + auth.token + '\r\n').encode('utf-8'))
sock.send(('NICK ' + auth.nickname + '\r\n').encode('utf-8'))
sock.send(('JOIN ' + auth.channel + '\r\n').encode('utf-8'))
sock.send(("CAP REQ :twitch.tv/tags\r\n").encode('utf-8'))

def floodProtection():
    global floodCounter
    while True:
        floodCounter = 0
        time.sleep(2.5)

def sendMessageQueue():
    while True:
        time.sleep(1.25)
        sock.send((messageQueue.get() + '\r\n').encode('utf-8'))

def livecheck():
    while True:
        headers = { 'Client-ID': auth.clientID }
        params = (('user_login', auth.channeluser),)
        response = requests.get('https://api.twitch.tv/helix/streams', headers=headers, params=params).json()
        if not response['data']:
            generalCollection.update_one( {'_id': 0}, {'$set': {'open': 1} } )
        else:
            generalCollection.update_one( {'_id': 0}, {'$set': {'open': 0} } )
        time.sleep(5)

floodProtectionThread = threading.Thread(target = floodProtection)
floodProtectionThread.start()

sendMessageQueueThread = threading.Thread(target = sendMessageQueue)
sendMessageQueueThread.start()

liveCheckThread = threading.Thread(target = livecheck)
liveCheckThread.start()

def queueMessage(message):
    msg = 'PRIVMSG ' + auth.channel + ' :' + message
    messageQueue.put(msg)

def sendMessage(message):
    global floodCounter
    if floodCounter == 0 and messageQueue.empty():
        msg = 'PRIVMSG ' + auth.channel + ' :' + message
        sock.send((msg + '\r\n').encode('utf-8'))
        floodCounter += 1

def sendNoFloodMessage(message):
    msg = 'PRIVMSG ' + auth.channel + ' :' + message
    sock.send((msg + '\r\n').encode('utf-8'))

def whisper(user, message):
    sendMessage('.w '+ user + ' ' + message)

def pong():
    sock.send("PONG\n".encode('utf-8'))

def start():
    repo = git.Repo(search_parent_directories=True)
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    sendMessage(emoji.emojize(':arrow_right:', use_aliases=True) + ' Dungeon Bot (' + branch + ', ' + sha[0:7] + ')')

start()

def ping():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        sendMessage('Dungeon Bot MrDestructoid For a list of commands, type +commands')

def commands():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        sendMessage(emoji.emojize(':memo:') + 'Commands: +register | +enterdungeon | +dungeonlvl | +lvl | +xp | +winrate | +dungeonmaster | +dungeonstats | +dungeonstatus')

def register():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        if userCollection.count_documents({'_id': username}, limit = 1) == 0:
            generalCollection.update_one( {'_id': 0}, {'$inc': {'dungeonlevel': 1} } )
            userCollection.insert_one( {'_id': username, 'userlevel': 1, 'total_experience': 0, 'current_experience': 0, 'dungeons': 0, 'dungeon_wins': 0, 'dungeon_losses': 0, 'entered': 0, 'enteredTime': 0, 'dungeonTimeout': 0} )
            sendMessage('DING PogChamp Dungeon Level [' + str(generalCollection.find_one( {'_id': 0 } )['dungeonlevel']) + ']')
        else:
            sendMessage(username + ', you are already a registered user! 4Head')

def dungeonlvl():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        sendMessage(emoji.emojize(':shield:', use_aliases=True) + ' Dungeon Level: [' + str(generalCollection.find_one( {'_id': 0} )['dungeonlevel']) + ']')

def userlvl():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        if message == '+lvl':
            if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
            else:
                sendMessage(username + "'s current level: [" + str(userCollection.find_one( {'_id': username } )['userlevel']) + '] - XP (' + str(int(userCollection.find_one( {'_id': username } )['current_experience'])) + ' / ' + str((((userCollection.find_one( {'_id': username } )['userlevel']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True))
        else:
            targetUser = re.search('lvl (.*)', message)
            if targetUser:
                targetUser = targetUser.group(1)
                if targetUser.lower() == username.lower():
                    if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                        sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
                    else:
                        sendMessage(username + "'s current level: [" + str(userCollection.find_one( {'_id': username } )['userlevel']) + '] - XP (' + str(int(userCollection.find_one( {'_id': username } )['current_experience'])) + ' / ' + str((((userCollection.find_one( {'_id': username } )['userlevel']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True))
                else:
                    if not checkusername(targetUser):
                        if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                            sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
                        else:
                            sendMessage(username + "'s current level: [" + str(userCollection.find_one( {'_id': username } )['userlevel']) + '] - XP (' + str(int(userCollection.find_one( {'_id': username } )['current_experience'])) + ' / ' + str((((userCollection.find_one( {'_id': username } )['userlevel']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True))
                    elif userCollection.count_documents( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) }, limit = 1) == 0:
                        sendMessage(username + ', no level found for that user!' + emoji.emojize (' :warning:'))
                    else:
                        sendMessage(str(userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['_id']) + '\'s current level: [' + str(userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['userlevel']) + '] - XP (' + str(userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['current_experience']) + ' / ' + str((((userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['userlevel']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True))

def userexperience():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        if message == '+xp':
            if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
            else:
                sendMessage(username + "'s total experience: " + str(int(userCollection.find_one( {'_id': username } )['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True))
        else:
            targetUser = re.search('xp (.*)', message)
            if targetUser:
                targetUser = targetUser.group(1)
                if targetUser.lower() == username.lower():
                    if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                        sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
                    else:
                        sendMessage(username + "'s total experience: " + str(int(userCollection.find_one( {'_id': username } )['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True))
                else:
                    if not checkusername(targetUser):
                        if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                            sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
                        else:
                            sendMessage(username + "'s total experience: " + str(int(userCollection.find_one( {'_id': username } )['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True))
                    elif userCollection.count_documents( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) }, limit = 1) == 0:
                        sendMessage(username + ', no experience found for that user!' + emoji.emojize(' :warning:'))
                    else:
                        sendMessage(str(userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['_id']) + '\'s total experience: ' + str(userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['total_experience']) + emoji.emojize(' :diamonds:', use_aliases=True))

def winrate():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        if message == '+winrate':
            if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
            elif userCollection.find_one( {'_id': username } )['dungeons'] == 0:
                sendMessage(username + ", you haven't entered any dungeons NotLikeThis")
            else:
                dungeons = userCollection.find_one( {'_id': username } )['dungeons']
                wins = userCollection.find_one( {'_id': username } )['dungeon_wins']
                losses = userCollection.find_one( {'_id': username } )['dungeon_losses']

                if wins == 1:
                    winWord = ' Win'
                else:
                    winWord = ' Wins'
                if losses == 1:
                    loseWord = ' Loss'
                else:
                    loseWord = ' Losses'
                sendMessage(username + "'s winrate: " + str(wins) + winWord +' / ' + str(losses) + loseWord + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))
        else:
            targetUser = re.search('winrate (.*)', message)
            if targetUser:
                targetUser = targetUser.group(1)
                if targetUser.lower() == username.lower():
                    if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                        sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
                    else:
                        dungeons = userCollection.find_one( {'_id': username} )['dungeons']
                        wins = userCollection.find_one( {'_id': username} )['dungeon_wins']
                        losses = userCollection.find_one( {'_id': username} )['dungeon_losses']

                        if wins == 1:
                            winWord = ' Win'
                        else:
                            winWord = ' Wins'
                        if losses == 1:
                            loseWord = ' Loss'
                        else:
                            loseWord = ' Losses'
                        sendMessage(username + "'s winrate: " + str(wins) + winWord +' / ' + str(losses) + loseWord + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))
                else:
                    if not checkusername(targetUser):
                        if userCollection.count_documents({'_id': username}, limit = 1) == 0:
                            sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))
                        else:
                            dungeons = userCollection.find_one( {'_id': username} )['dungeons']
                            wins = userCollection.find_one( {'_id': username} )['dungeon_wins']
                            losses = userCollection.find_one( {'_id': username} )['dungeon_losses']

                            if wins == 1:
                                winWord = ' Win'
                            else:
                                winWord = ' Wins'
                            if losses == 1:
                                loseWord = ' Loss'
                            else:
                                loseWord = ' Losses'
                            sendMessage(username + "'s winrate: " + str(wins) + winWord +' / ' + str(losses) + loseWord + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))
                    elif userCollection.count_documents( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) }, limit = 1) == 0:
                        sendMessage(username + ', that user is not registered!' + emoji.emojize(' :warning:'))
                    elif userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['dungeons'] == 0:
                        sendMessage(username + ", that user hasn't entered any dungeons NotLikeThis")
                    else:
                        dungeons = userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['dungeons']
                        wins = userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['dungeon_wins']
                        losses = userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['dungeon_losses']

                        if wins == 1:
                            winWord = ' Win'
                        else:
                            winWord = ' Wins'
                        if losses == 1:
                            loseWord = ' Loss'
                        else:
                            loseWord = ' Losses'
                        sendMessage(str(userCollection.find_one( {'_id': re.compile('^' + re.escape(targetUser) + '$', re.IGNORECASE) } )['_id']) + '\'s winrate: ' + str(wins) + winWord +' / ' + str(losses) + loseWord + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))

def enterdungeon():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        if userCollection.count_documents({'_id': username}, limit = 1) != 0:
            if int((userCollection.find_one( {'_id': username})['dungeonTimeout']) - (time.time() - (userCollection.find_one( {'_id': username})['enteredTime']))) < 0:
                opendungeon(username)
            if userCollection.find_one( {'_id': username})['entered'] == 0:
                dungeonlevel = generalCollection.find_one( {'_id': 0 } )['dungeonlevel']
                userlevel = userCollection.find_one( {'_id': username})['userlevel']

                if message == '+enterdungeon':
                    if userlevel > dungeonlevel:
                        levelRun = dungeonlevel
                        successRate = 65-((dungeonlevel-userlevel)*7)
                        experienceGain = int(100*dungeonlevel)*(1.2**(dungeonlevel-userlevel))
                        dungeonTimeout = 600-(60*(userlevel-dungeonlevel))
                    else:
                        levelRun = userlevel
                        successRate = 65
                        experienceGain = int(100*userlevel)
                        dungeonTimeout = 600
                else:
                    targetNumber = re.search('enterdungeon (.*)', message)
                    if targetNumber:
                        targetNumber = targetNumber.group(1)
                        if targetNumber.isdigit() == False:
                            if userlevel > dungeonlevel:
                                levelRun = dungeonlevel
                                successRate = 65-((dungeonlevel-userlevel)*7)
                                experienceGain = int(100*dungeonlevel)*(1.2**(dungeonlevel-userlevel))
                                dungeonTimeout = 600-(60*(userlevel-dungeonlevel))
                            else:
                                levelRun = userlevel
                                successRate = 65
                                experienceGain = int(100*userlevel)
                                dungeonTimeout = 600
                        elif int(targetNumber) <= 0:
                            sendMessage(username + ', the Dungeon [' + targetNumber + "] is too low level for you to enter. You can't enter dungeons below level 1" + emoji.emojize(' :crossed_swords:'))
                            return
                        elif int(targetNumber) > dungeonlevel:
                            sendMessage(username + ', the Dungeon is currently level [' + str(dungeonlevel) + "] - You can't venture beyond this level yet" + emoji.emojize(' :crossed_swords:'))
                            return
                        elif int(targetNumber) > (userlevel + 5):
                            sendMessage(username + ', the Dungeon [' + targetNumber + "] is too high level for you to enter. You can't enter dungeons that exceed 5 levels above your own" + emoji.emojize(' :crossed_swords:'))
                            return
                        else:
                            levelRun = int(targetNumber)
                            successRate = 65-((int(targetNumber)-userlevel)*7)
                            experienceGain = (100*int(targetNumber))*(1.2**(int(targetNumber)-userlevel))
                            dungeonTimeout = 600-(60*(userlevel-int(targetNumber)))
                    else:
                        return

                dungeonSuccess = random.randint(1, 101)
                userCollection.update_one( {'_id': username}, {'$set': {'entered': 1} } )
                userCollection.update_one( {'_id': username}, {'$set': {'dungeonTimeout': dungeonTimeout} } )
                userCollection.update_one( {'_id': username}, {'$set': {'enteredTime': time.time()} } )

                if dungeonSuccess <= successRate:
                    rareRunQuality = random.randint(1, 101)
                    if rareRunQuality <= 10:
                        experienceGain = int(experienceGain*0.5)
                        queueMessage(username + ' | Very Bad Run [x0.5] - You beat the dungeon level [' + str(levelRun) + '] - Experience Gained: ' + str(experienceGain) + ' PogChamp')
                        userCollection.update_one( {'_id': username}, {'$inc': { 'total_experience': experienceGain } } )
                        userCollection.update_one( {'_id': username}, {'$inc': { 'current_experience': experienceGain } } )
                        generalCollection.update_one( {'_id': 0}, {'$inc': { 'total_experience': experienceGain } } )
                    elif rareRunQuality >= 90:
                        experienceGain = int(experienceGain*1.5)
                        queueMessage(username + ' | Very Good Run [x1.5] - You beat the dungeon level [' + str(levelRun) + '] - Experience Gained: ' + str(experienceGain) + ' PogChamp')
                        userCollection.update_one( {'_id': username}, {'$inc': { 'total_experience': experienceGain } } )
                        userCollection.update_one( {'_id': username}, {'$inc': { 'current_experience': experienceGain } } )
                        generalCollection.update_one( {'_id': 0}, {'$inc': { 'total_experience': experienceGain } } )
                    else:
                        normalRunQuality = random.randint(75,126)
                        experienceGain = int(experienceGain*normalRunQuality*0.01)
                        if normalRunQuality < 100:
                            queueMessage(username + ' | Bad Run [x' + str(round(normalRunQuality*0.01, 2)) + '] - You beat the dungeon level [' + str(levelRun) + '] - Experience Gained: ' + str(experienceGain) + ' PogChamp')
                        else:
                            queueMessage(username + ' | Good Run [x' + str(round(normalRunQuality*0.01, 2)) + '] - You beat the dungeon level [' + str(levelRun) + '] - Experience Gained: ' + str(experienceGain) + ' PogChamp')
                        userCollection.update_one( {'_id': username}, {'$inc': { 'total_experience': experienceGain } } )
                        userCollection.update_one( {'_id': username}, {'$inc': { 'current_experience': experienceGain } } )
                        generalCollection.update_one( {'_id': 0}, {'$inc': { 'total_experience': experienceGain } } )
                    userCollection.update_one( {'_id': username}, {'$inc': { 'dungeon_wins': 1 } } )
                    generalCollection.update_one( {'_id': 0}, {'$inc': { 'total_wins': 1 } } )
                    if (((userlevel+1)**2)*100) - userCollection.find_one( {'_id': username})['current_experience'] <= 0:
                        while (((userCollection.find_one( {'_id': username})['userlevel']+1)**2)*100) - userCollection.find_one( {'_id': username})['current_experience'] <= 0:
                            userCollection.update_one( {'_id': username}, {'$inc': { 'userlevel': 1 } } )
                            userCollection.update_one( {'_id': username}, {'$inc': { 'current_experience': -(((userCollection.find_one( {'_id': username})['userlevel'])**2)*100) } } )
                        queueMessage(username + ' just leveled up! Level - [' + str(userCollection.find_one( {'_id': username})['userlevel']) + '] PogChamp')
                else:
                    queueMessage(username + ', you failed to beat the dungeon level [' + str(levelRun) + '] - No experience gained FeelsBadMan')
                    userCollection.update_one( {'_id': username}, {'$inc': { 'dungeon_losses': 1 } } )
                    generalCollection.update_one( {'_id': 0}, {'$inc': { 'total_losses': 1 } } )
                userCollection.update_one( {'_id': username}, {'$inc': { 'dungeons': 1 } } )
                generalCollection.update_one( {'_id': 0}, {'$inc': { 'total_dungeons': 1 } } )
            else:
                sendMessage(username + ', you have already entered the dungeon recently, ' + str(datetime.timedelta(seconds=(int((userCollection.find_one( {'_id': username})['dungeonTimeout']) - (time.time() - (userCollection.find_one( {'_id': username})['enteredTime'])))))) + ' left until you can enter again!' + emoji.emojize(' :hourglass:', use_aliases=True))
        else:
            sendMessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))

opendungeonLock = threading.Lock()

def opendungeon(username):
    opendungeonLock.acquire()
    userCollection.update_one( {'_id': username}, {'$set': {'entered': 0} } )
    userCollection.update_one( {'_id': username}, {'$set': {'enteredTime': 0} } )
    userCollection.update_one( {'_id': username}, {'$set': {'dungeonTimeout': 0} } )
    opendungeonLock.release()

def dungeonmaster():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        topUser = userCollection.find_one(sort=[('total_experience', -1)])
        if topUser:
            highestExperience = topUser['total_experience']
            numberOftopUsers = userCollection.count_documents( {'total_experience': highestExperience} )
            if numberOftopUsers == 1:
                sendMessage(str(userCollection.find_one( {'total_experience': highestExperience} )['_id']) + ' is the current Dungeon Master with ' + str(highestExperience) + ' experience' + emoji.emojize(' :crown:'))
            else:
                sendMessage('There are ' + str(numberOftopUsers) + ' users with ' + str(highestExperience) + ' experience, no one is currently Dungeon Master FeelsBadMan')
        else:
            sendMessage('There is currently no Dungeon Master FeelsBadMan')

def dungeonstatus():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        uptime = time.time()
        sendMessage('Dungeon Uptime: ' + str(datetime.timedelta(seconds=(int(uptime - botStart)))) + emoji.emojize(' :stopwatch:'))

def dungeonstats():
    if generalCollection.find_one( {'_id': 0} )['open'] == 1:
        total_dungeons = generalCollection.find_one( {'_id': 0} )['total_dungeons']
        total_wins = generalCollection.find_one( {'_id': 0} )['total_wins']
        total_losses = generalCollection.find_one( {'_id': 0} )['total_losses']
        if total_dungeons == 1:
            dungeonWord = ' Dungeon'
        else:
            dungeonWord = ' Dungeons'
        if total_wins == 1:
            winWord = ' Win'
        else:
            winWord = ' Wins'
        if total_losses == 1:
            loseWord = ' Loss'
        else:
            loseWord = ' Losses'
        if total_dungeons != 0:
            sendMessage('General Dungeon Stats: ' + str(total_dungeons) + dungeonWord + ' / ' + str(total_wins) + winWord +' / ' + str(total_losses) + loseWord + ' = ' + str((((total_wins)/(total_dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))
        else:
            sendMessage('General Dungeon Stats: ' + str(total_dungeons) + dungeonWord + ' / ' + str(total_wins) + winWord +' / ' + str(total_losses) + loseWord + ' = ' + '0% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))

def usertag():
    if tagCollection.find_one( {'_id': username} )['admin'] == 1:
        target = re.search('tag (.*)', message)
        if target:
            tagList = ['admin', 'moderator']
            target = target.group(1).split()
            if checkusername(target[0]):
                if target[1].lower() in tagList:
                    tagCollection.update_one( {'_id': checkusername(target[0]) }, {'$set': {target[1].lower(): 1} }, upsert=True )

def hardreset():
    if tagCollection.find_one( {'_id': username} )['admin'] == 1:
        generalCollection.update_one( {'_id': 0}, {'$set': {'dungeonlevel': 0} } )
        generalCollection.update_one( {'_id': 0}, {'$set': {'total_experience': 0} } )
        generalCollection.update_one( {'_id': 0}, {'$set': {'total_dungeons': 0} } )
        generalCollection.update_one( {'_id': 0}, {'$set': {'total_wins': 0} } )
        generalCollection.update_one( {'_id': 0}, {'$set': {'total_losses': 0} } )
        userCollection.drop()

def resetcd():
    if tagCollection.find_one( {'_id': username} )['admin'] == 1:
        for user in userCollection.find():
            userCollection.update_one( {'_id': user['_id']}, {'$set': {'entered': 0} } )
            userCollection.update_one( {'_id': user['_id']}, {'$set': {'enteredTime': 0} } )
            userCollection.update_one( {'_id': user['_id']}, {'$set': {'dungeonTimeout': 0} } )
        sendMessage('Cooldowns reset for all users' + emoji.emojize(' :stopwatch:'))

def restart():
    if tagCollection.find_one( {'_id': username} )['admin'] == 1:
        repo = git.Repo(search_parent_directories=True)
        repo.git.reset('--hard')
        repo.remotes.origin.pull()
        os.system('kill %d' % os.getpid())

def checkusername(user):
    headers = { 'Client-ID': auth.clientID }
    params = (('login', user),)
    response = requests.get('https://api.twitch.tv/helix/users', headers=headers, params=params).json()
    if 'error' in response:
        return
    elif 'data' in response:
        return response['data'][0]['display_name']
    else:
        return

while True:
    resp = emoji.demojize(sock.recv(2048).decode('utf-8'))

    if resp.startswith('PING'):
        pong()

    elif len(resp) > 0:
        username = re.search('display-name=(.+?);', resp)
        if username:
            username = username.group(1)
        message = re.search(':(.*)\s:(.*)', resp)
        if message:
            message = message.group(2).strip()
            if (message == '!ping' or message == '+ping') and floodCounter == 0:
                ping()
            if message == '+commands' and floodCounter == 0:
                commands()
            if message == '+register' and floodCounter == 0:
                register()
            if message == '+dungeonlvl' and floodCounter == 0:
                dungeonlvl()
            if message.startswith('+lvl') and floodCounter == 0:
                userlvl()
            if message.startswith('+xp') and floodCounter == 0:
                userexperience()
            if message.startswith('+winrate') and floodCounter == 0:
                winrate()
            if message.startswith('+enterdungeon') and floodCounter == 0:
                enterdungeon()
                floodCounter += 1
            if message == '+dungeonmaster' and floodCounter == 0:
                dungeonmaster()
            if message == '+dungeonstatus' and floodCounter == 0:
                dungeonstatus()
            if message == '+dungeonstats' and floodCounter == 0:
                dungeonstats()
            if message.startswith('+tag'):
                usertag()
            if message == '+hardreset':
                hardreset()
            if message == '+resetcd':
                resetcd()
            if message == '+restart':
                restart()
