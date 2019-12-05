import datetime
import random
import re
import time
import utility as util

import emoji

import database as opt
import schemes

db = opt.MongoDatabase
botstart = time.time()

### User Commands ###

def commands():
    util.sendmessage(emoji.emojize(':memo:', use_aliases=True) + 'Commands: +register | +enterdungeon | +dungeonlvl | +lvl | +xp | +winrate | +dungeonmaster | +dungeonstats | +dungeonstatus')

def enterdungeon(username, message):
    user = db(opt.USERS).find_one_by_id(username)
    if user != None:
        if int(user['next_entry']- time.time()) < 0:
            util.opendungeon(username)
            user = db(opt.USERS).find_one_by_id(username)
        if user['entered'] == 0:
            dungeon = db(opt.DUNGEONS).find_one_by_id(0)
            dungeonlevel = dungeon['dungeon_level']
            userlevel = user['user_level']

            if userlevel > dungeonlevel:
                levelrun = dungeonlevel
                successrate = 65+((userlevel-dungeonlevel)*7)
                successrate = successrate if successrate <= 100 else 100
                experiencegain = int(100*dungeonlevel)*(1-((userlevel-dungeonlevel))*0.2)
                experiencegain = experiencegain if experiencegain >= 0 else 0
                dungeontimeout = 600
            else:
                levelrun = userlevel
                successrate = 65
                experiencegain = int(100*userlevel)
                dungeontimeout = 600

            if experiencegain == 0:
                util.sendmessage(username + ', the Dungeon [' + str(dungeonlevel) + "] is too low level for you to enter. You won't gain any experience " + emoji.emojize(':crossed_swords:', use_aliases=True))
                return

            dungeonsuccess = random.randint(1, 101)
            db(opt.USERS).update_one(username, {'$set': {
                'entered': 1,
                'last_entry': time.time(),
                'next_entry': time.time() + dungeontimeout
            }})

            if dungeonsuccess <= successrate:
                rarerunquality = random.randint(1, 101)
                if rarerunquality <= 10:
                    experiencegain = int(experiencegain*0.5)
                    util.queuemessage(username + ' | Very Bad Run [x0.5] - You beat the dungeon level [' + str(levelrun) + '] - Experience Gained: ' + str(experiencegain) + ' PogChamp')
                elif rarerunquality >= 90:
                    experiencegain = int(experiencegain*1.5)
                    util.queuemessage(username + ' | Very Good Run [x1.5] - You beat the dungeon level [' + str(levelrun) + '] - Experience Gained: ' + str(experiencegain) + ' PogChamp')
                else:
                    normalrunquality = random.randint(75,126)
                    experiencegain = int(experiencegain*normalrunquality*0.01)
                    if normalrunquality < 100:
                        util.queuemessage(username + ' | Bad Run [x' + str(round(normalrunquality*0.01, 2)) + '] - You beat the dungeon level [' + str(levelrun) + '] - Experience Gained: ' + str(experiencegain) + ' PogChamp')
                    else:
                        util.queuemessage(username + ' | Good Run [x' + str(round(normalrunquality*0.01, 2)) + '] - You beat the dungeon level [' + str(levelrun) + '] - Experience Gained: ' + str(experiencegain) + ' PogChamp')
                db(opt.USERS).update_one(username, {'$inc': {
                    'total_experience': experiencegain,
                    'current_experience': experiencegain,
                    'dungeon_wins': 1
                }})
                db(opt.DUNGEONS).update_one(0, {'$inc': {
                    'total_experience': experiencegain,
                    'total_wins': 1
                }})
                user_calculated_experience = user['current_experience'] + experiencegain
                if (((userlevel+1)**2)*100) - user_calculated_experience <= 0:
                    while (((user['user_level']+1)**2)*100) - user_calculated_experience <= 0:
                        db(opt.USERS).update_one(username, {'$inc': {
                            'user_level': 1,
                            'current_experience': -(((user['user_level'])**2)*100)
                        }})
                    util.queuemessage(username + ' just leveled up! Level - [' + str(user['user_level'] + 1) + '] PogChamp')
            else:
                db(opt.USERS).update_one(username, { '$inc': { 'dungeon_losses': 1 } })
                db(opt.DUNGEONS).update_one(0, { '$inc': { 'total_losses': 1 } })
                util.queuemessage(username + ', you failed to beat the dungeon level [' + str(levelrun) + '] - No experience gained FeelsBadMan')
            db(opt.USERS).update_one(username, { '$inc': { 'dungeons': 1 } })
            db(opt.DUNGEONS).update_one(0, { '$inc': { 'total_dungeons': 1 } })
        else:
            util.sendmessage(username + ', you have already entered the dungeon recently, ' + str(datetime.timedelta(seconds=(int(user['next_entry']) - time.time()))) + ' left until you can enter again!' + emoji.emojize(' :hourglass:', use_aliases=True))
    else:
        util.sendmessage(username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:'))

def dungeonlvl():
    dungeon = db(opt.DUNGEONS).find_one_by_id(0)
    util.sendmessage(emoji.emojize(':shield:', use_aliases=True) + ' Dungeon Level: [' + str(dungeon['dungeon_level']) + ']')

def dungeonmaster():
    topuser = db(opt.USERS).find_one(sort=[('total_experience', -1)])
    if topuser:
        highestexperience = topuser['total_experience']
        numberoftopusers = db(opt.USERS).count_documents( {'total_experience': highestexperience} )
        if numberoftopusers == 1:
            thetopuser = db(opt.USERS).find_one( {'total_experience': highestexperience} )
            util.sendmessage(str(thetopuser['_id']) + ' is the current Dungeon Master with ' + str(highestexperience) + ' experience' + emoji.emojize(' :crown:', use_aliases=True))
        else:
            util.sendmessage('There are ' + str(numberoftopusers) + ' users with ' + str(highestexperience) + ' experience, no one is currently Dungeon Master FeelsBadMan')
    else:
        util.sendmessage('There is currently no Dungeon Master FeelsBadMan')

def dungeonstats():
    dungeon = db(opt.DUNGEONS).find_one_by_id(0)
    dungeons = dungeon['total_dungeons']
    wins = dungeon['total_wins']
    losses = dungeon['total_losses']
    if dungeons == 1:
        dungeonword = ' Dungeon'
    else:
        dungeonword = ' Dungeons'
    if wins == 1:
        winword = ' Win'
    else:
        winword = ' Wins'
    if losses == 1:
        loseword = ' Loss'
    else:
        loseword = ' Losses'
    if dungeons != 0:
        util.sendmessage('General Dungeon Stats: ' + str(dungeons) + dungeonword + ' / ' + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))
    else:
        util.sendmessage('General Dungeon Stats: ' + str(dungeons) + dungeonword + ' / ' + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + '0% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))

def dungeonstatus():
    uptime = time.time()
    util.sendmessage('Dungeon Uptime: ' + str(datetime.timedelta(seconds=(int(uptime - botstart)))) + emoji.emojize(' :stopwatch:', use_aliases=True))

def ping():
    util.sendmessage('Dungeon Bot MrDestructoid For a list of commands, type +commands')

def register(username):
    user = db(opt.USERS).find_one_by_id(username)
    if user == None:
        db(opt.DUNGEONS).update_one(0, { '$inc': { 'dungeon_level': 1 } })
        db(opt.USERS).update_one(username, { '$set': schemes.USER }, upsert=True)
        user = db(opt.USERS).find_one_by_id(username)
        util.queuemessage('DING PogChamp Dungeon Level [' + str(user['dungeon_level']) + ']')
    else:
        util.sendmessage(username + ', you are already a registered user! 4Head')

def userexperience(username, message):
    if message == '+xp' or message == 'exp':
        registered = util.checkuserregistered(username)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            util.sendmessage(username + "'s total experience: " + str(int(user['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True))
    else:
        targetuser = re.search('(?:xp|exp) (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if targetuser.lower() == username.lower():
                registered = util.checkuserregistered(username)
                if registered:
                    user = db(opt.USERS).find_one_by_id(username)
                    util.sendmessage(username + "'s total experience: " + str(int(user['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True))
            else:
                targetusername = re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE)
                target = db(opt.USERS).find_one_by_id(targetusername)
                if not util.checkusername(targetuser):
                    registered = util.checkuserregistered(username)
                    if registered:
                        user = db(opt.USERS).find_one_by_id(username)
                        util.sendmessage(username + "'s total experience: " + str(int(user['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True))
                elif target:
                    util.sendmessage(str(target['_id']) + '\'s total experience: ' + str(target['total_experience']) + emoji.emojize(' :diamonds:', use_aliases=True))
                else:
                    util.sendmessage(username + ', no experience found for that user!' + emoji.emojize(' :warning:', use_aliases=True))

def userlevel(username, message):
    if message == '+lvl' or message == '+level':
        registered = util.checkuserregistered(username)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            util.sendmessage(username + "'s current level: [" + str(user['user_level']) + '] - XP (' + str(int(user['current_experience'])) + ' / ' + str((((user['user_level']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True))
    else:
        targetuser = re.search('(?:lvl|level) (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if targetuser.lower() == username.lower():
                registered = util.checkuserregistered(username)
                if registered:
                    user = db(opt.USERS).find_one_by_id(username)
                    util.sendmessage(username + "'s current level: [" + str(user['user_level']) + '] - XP (' + str(int(user['current_experience'])) + ' / ' + str((((user['user_level']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True))
            else:
                targetusername = re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE)
                target = db(opt.USERS).find_one_by_id(targetusername)
                if not util.checkusername(targetuser):
                    registered = util.checkuserregistered(username)
                    if registered:
                        user = db(opt.USERS).find_one_by_id(username)
                        util.sendmessage(username + "'s current level: [" + str(user['user_level']) + '] - XP (' + str(int(user['current_experience'])) + ' / ' + str((((user['user_level']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True))
                elif target:
                    util.sendmessage(str(target['_id']) + '\'s current level: [' + str(target['user_level']) + '] - XP (' + str(target['current_experience']) + ' / ' + str((((target['user_level']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True))
                else:
                    util.sendmessage(username + ', no level found for that user!' + emoji.emojize (' :warning:'))

def winrate(username, message):
    if message == '+winrate':
        registered = util.checkuserregistered(username)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            if user['dungeons'] == 0:
                util.sendmessage(username + ", you haven't entered any dungeons NotLikeThis")
            else:
                dungeons = user['dungeons']
                wins = user['dungeon_wins']
                losses = user['dungeon_losses']

                if wins == 1:
                    winword = ' Win'
                else:
                    winword = ' Wins'
                if losses == 1:
                    loseword = ' Loss'
                else:
                    loseword = ' Losses'
                util.sendmessage(username + "'s winrate: " + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))
    else:
        targetuser = re.search('winrate (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if (targetuser.lower() == username.lower()) or not util.checkusername(targetuser):
                registered = util.checkuserregistered(username)
                if registered:
                    user = db(opt.USERS).find_one_by_id(username)
                    if user['dungeons'] == 0:
                        util.sendmessage(username + ", you haven't entered any dungeons NotLikeThis")
                    else:
                        dungeons = user['dungeons']
                        wins = user['dungeon_wins']
                        losses = user['dungeon_losses']
                        if wins == 1:
                            winword = ' Win'
                        else:
                            winword = ' Wins'
                        if losses == 1:
                            loseword = ' Loss'
                        else:
                            loseword = ' Losses'
                        util.sendmessage(username + "'s winrate: " + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))
            else:
                targetusername = re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE)
                registered = util.checkuserregistered(targetusername)
                if registered:
                    target = db(opt.USERS).find_one_by_id(targetusername)
                    if target['dungeons'] == 0:
                        util.sendmessage(username + ", that user hasn't entered any dungeons NotLikeThis")
                    else:
                        dungeons = target['dungeons']
                        wins = target['dungeon_wins']
                        losses = target['dungeon_losses']
                        if wins == 1:
                            winword = ' Win'
                        else:
                            winword = ' Wins'
                        if losses == 1:
                            loseword = ' Loss'
                        else:
                            loseword = ' Losses'
                        util.sendmessage(str(target['_id']) + '\'s winrate: ' + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True))
