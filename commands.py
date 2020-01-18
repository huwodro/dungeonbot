import datetime
import random
import re
import threading
import time

import utility as util
import database as opt
import schemes
import messages

db = opt.MongoDatabase
botstart = time.time()

### User Commands ###

def commands(channel):
    util.sendmessage(messages.commands, channel)

def enterdungeon(username, message, channel):
    user = db(opt.USERS).find_one_by_id(username)
    if user is not None and user.get('user_level') is not None:
        entertime = time.time()
        if int(user['next_entry'] - entertime) <= 0:
            util.opendungeon(username)
            user = db(opt.USERS).find_one_by_id(username)
        if user['entered'] == 0:
            dungeon = db(opt.GENERAL).find_one_by_id(0)
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
                util.sendmessage(messages.dungeon_too_low_level(username, str(dungeonlevel)), channel)
                return

            dungeonsuccess = random.randint(1, 101)
            db(opt.USERS).update_one(username, {'$set': {
                'entered': 1,
                'last_entry': entertime,
                'next_entry': entertime + dungeontimeout
            }})

            if dungeonsuccess <= successrate:
                rarerunquality = random.randint(1, 101)
                if rarerunquality <= 10:
                    experiencegain = int(experiencegain*0.5)
                    util.sendmessage(messages.dungeon_very_bad_run(username, str(levelrun), str(experiencegain)), channel)
                elif rarerunquality >= 90:
                    experiencegain = int(experiencegain*1.5)
                    util.sendmessage(messages.dungeon_very_good_run(username, str(levelrun), str(experiencegain)), channel)
                else:
                    normalrunquality = random.randint(75,126)
                    experiencegain = int(experiencegain*normalrunquality*0.01)
                    if normalrunquality < 100:
                        util.sendmessage(messages.dungeon_bad_run(username, str(round(normalrunquality*0.01, 2)), str(levelrun), str(experiencegain)), channel)
                    else:
                        util.sendmessage(messages.dungeon_good_run(username, str(round(normalrunquality*0.01, 2)), str(levelrun), str(experiencegain)), channel)
                db(opt.USERS).update_one(username, {'$inc': {
                    'total_experience': experiencegain,
                    'current_experience': experiencegain,
                    'dungeon_wins': 1
                }})
                db(opt.GENERAL).update_one(0, {'$inc': {
                    'total_experience': experiencegain,
                    'total_wins': 1
                }})
                user_calculated_experience = user['current_experience'] + experiencegain
                if (((userlevel+1)**2)*100) - user_calculated_experience <= 0:
                    db(opt.USERS).update_one(username, {'$inc': {
                        'user_level': 1,
                        'current_experience': -(((user['user_level']+1)**2)*100)
                    }})
                    levelupthread = threading.Thread(target = levelup, args=(username, str(user['user_level'] + 1), channel))
                    levelupthread.start()
            else:
                db(opt.USERS).update_one(username, { '$inc': { 'dungeon_losses': 1 } })
                db(opt.GENERAL).update_one(0, { '$inc': { 'total_losses': 1 } })
                util.sendmessage(messages.dungeon_failed(username, str(levelrun)), channel)
            db(opt.USERS).update_one(username, { '$inc': { 'dungeons': 1 } })
            db(opt.GENERAL).update_one(0, { '$inc': { 'total_dungeons': 1 } })
        else:
            util.sendmessage(messages.dungeon_already_entered(username, str(datetime.timedelta(seconds=(int(user['next_entry']) - entertime))).split('.')[0]), channel)
    else:
        util.sendmessage(messages.you_not_registered(username), channel)

def levelup(username, message, channel):
    util.queuemessage(messages.user_level_up(username, message), 0, channel)

def dungeonlvl(channel):
    dungeon = db(opt.GENERAL).find_one_by_id(0)
    util.sendmessage(messages.dungeon_level(str(dungeon['dungeon_level'])), channel)

def dungeonmaster(channel):
    topuser = db(opt.USERS).find_one(sort=[('total_experience', -1)])
    if topuser and topuser.get('user_level'):
        highestexperience = topuser['total_experience']
        userlevel = topuser['user_level']
        numberoftopusers = db(opt.USERS).count_documents( {'total_experience': highestexperience} )
        if numberoftopusers == 1:
            thetopuser = db(opt.USERS).find_one( {'total_experience': highestexperience} )
            util.sendmessage(messages.dungeon_master(thetopuser['_id'], str(highestexperience), str(userlevel)), channel)
        else:
            util.sendmessage(messages.dungeon_masters(str(numberoftopusers), str(highestexperience), str(userlevel)), channel)
    else:
        util.sendmessage(messages.dungeon_no_master, channel)

def dungeonstats(channel):
    general = db(opt.GENERAL).find_one_by_id(0)
    try:
        dungeons = general['total_dungeons']
    except:
        dungeons = 0
    try:
        wins = general['total_wins']
    except:
        wins = 0
    try:
        losses = general['total_losses']
    except:
        losses = 0
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
    if dungeons is not 0:
        util.sendmessage(messages.dungeon_general_stats(str(dungeons), dungeonword, str(wins), winword, str(losses), loseword, str(round((((wins)/(dungeons))*100), 3))), channel)
    else:
        util.sendmessage(messages.dungeon_general_stats(str(dungeons), dungeonword, str(wins), winword, str(losses), loseword, '0'), channel)

def raidstats(channel):
    general = db(opt.GENERAL).find_one_by_id(0)
    try:
        raids = general['total_raids']
    except:
        raids = 0
    try:
        wins = general['total_raid_wins']
    except:
        wins = 0
    try:
        losses = general['total_raid_losses']
    except:
        losses = 0
    if raids == 1:
        raidword = ' Raid'
    else:
        raidword = ' Raids'
    if wins == 1:
        winword = ' Win'
    else:
        winword = ' Wins'
    if losses == 1:
        loseword = ' Loss'
    else:
        loseword = ' Losses'
    if raids is not 0:
        util.sendmessage(messages.raid_general_stats(str(raids), raidword, str(wins), winword, str(losses), loseword, str(round((((wins)/(raids))*100), 3))), channel)
    else:
        util.sendmessage(messages.raid_general_stats(str(raids), raidword, str(wins), winword, str(losses), loseword, '0'), channel)

def dungeonstatus(channel):
    uptime = time.time()
    util.sendmessage(messages.dungeon_uptime(str(datetime.timedelta(seconds=(int(uptime - botstart))))), channel)

def register(username, channel):
    user = db(opt.USERS).find_one_by_id(username)
    if user == None or user.get('user_level') == None:
        db(opt.GENERAL).update_one(0, { '$inc': { 'dungeon_level': 1 } })
        db(opt.USERS).update_one(username, { '$set': schemes.USER }, upsert=True)
        dungeon = db(opt.GENERAL).find_one_by_id(0)
        util.sendmessage(messages.dungeon_level_up(str(dungeon['dungeon_level'])), channel)
    else:
        util.sendmessage(messages.user_already_registered(username), channel)

def userexperience(username, channel, message=None):
    if message is None:
        registered = util.checkuserregistered(username, channel)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            util.sendmessage(messages.user_experience(username, str(user['total_experience'])), channel)
    else:
        if message.lower() == username.lower():
            registered = util.checkuserregistered(username, channel)
            if registered:
                user = db(opt.USERS).find_one_by_id(username)
                util.sendmessage(messages.user_experience(username, str(user['total_experience'])), channel)
        else:
            target = re.compile('^' + re.escape(message) + '$', re.IGNORECASE)
            user = db(opt.USERS).find_one_by_id(target)
            if not util.checkusername(message):
                registered = util.checkuserregistered(username, channel)
                if registered:
                    user = db(opt.USERS).find_one_by_id(username)
                    util.sendmessage(messages.user_experience(username, str(user['total_experience'])), channel)
            elif user:
                util.sendmessage(messages.user_experience(user['_id'], str(user['total_experience'])), channel)
            else:
                util.sendmessage(messages.user_no_experience(username), channel)

def userlevel(username, channel, message=None):
    if message is None:
        registered = util.checkuserregistered(username, channel)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            util.sendmessage(messages.user_level(username, str(user['user_level']), str(user['current_experience']), str((((user['user_level']) + 1)**2)*100)), channel)
    else:
        if message.lower() == username.lower():
            registered = util.checkuserregistered(username, channel)
            if registered:
                user = db(opt.USERS).find_one_by_id(username)
                util.sendmessage(messages.user_level(username, str(user['user_level']), str(user['current_experience']), str((((user['user_level']) + 1)**2)*100)), channel)
        else:
            target = re.compile('^' + re.escape(message) + '$', re.IGNORECASE)
            user = db(opt.USERS).find_one_by_id(target)
            if not util.checkusername(message):
                registered = util.checkuserregistered(username, channel)
                if registered:
                    user = db(opt.USERS).find_one_by_id(username)
                    util.sendmessage(messages.user_level(username, str(user['user_level']), str(user['current_experience']), str((((user['user_level']) + 1)**2)*100)), channel)
            elif user:
                util.sendmessage(messages.user_level(user['_id'], str(user['user_level']), str(user['current_experience']), str((((user['user_level']) + 1)**2)*100)), channel)
            else:
                util.sendmessage(messages.user_no_level(username), channel)

def winrate(username, channel, message=None):
    if message is None:
        registered = util.checkuserregistered(username, channel)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            if user['dungeons'] == 0:
                util.sendmessage(messages.you_no_entered_dungeons(username), channel)
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
                util.sendmessage(messages.user_stats(username, str(wins), winword, str(losses), loseword, str(round((((wins)/(dungeons))*100), 3))), channel)
    else:
        if (message.lower() == username.lower()) or not util.checkusername(message):
            registered = util.checkuserregistered(username, channel)
            if registered:
                user = db(opt.USERS).find_one_by_id(username)
                if user['dungeons'] == 0:
                    util.sendmessage(messages.you_no_entered_dungeons(username), channel)
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
                    util.sendmessage(messages.user_stats(username, str(wins), winword, str(losses), loseword, str(round((((wins)/(dungeons))*100), 3))), channel)
        else:
            target = re.compile('^' + re.escape(message) + '$', re.IGNORECASE)
            registered = util.checkuserregistered(username, channel, target)
            if registered:
                user = db(opt.USERS).find_one_by_id(target)
                if user is not None and user['dungeons'] is 0:
                    util.sendmessage(messages.user_no_entered_dungeons(username), channel)
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
                    util.sendmessage(messages.user_stats(user['_id'], str(wins), winword, str(losses), loseword, str(round((((wins)/(dungeons))*100), 3))), channel)
