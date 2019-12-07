import datetime
import random
import re
import time
import utility as util

import emoji

import database as opt
import schemes
import messages

db = opt.MongoDatabase
botstart = time.time()

### User Commands ###

def commands():
    util.sendmessage(messages.commands)

def enterdungeon(username, message):
    user = db(opt.USERS).find_one_by_id(username)
    if user is not None:
        if int(user['next_entry']- time.time()) < 0:
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
                util.sendmessage(messages.dungeon_too_low_level(username, str(dungeonlevel)))
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
                    util.sendmessage(messages.dungeon_very_bad_run(username, str(levelrun), str(experiencegain)))
                elif rarerunquality >= 90:
                    experiencegain = int(experiencegain*1.5)
                    util.sendmessage(messages.dungeon_very_good_run(username, str(levelrun), str(experiencegain)))
                else:
                    normalrunquality = random.randint(75,126)
                    experiencegain = int(experiencegain*normalrunquality*0.01)
                    if normalrunquality < 100:
                        util.sendmessage(messages.dungeon_bad_run(username, str(round(normalrunquality*0.01, 2)), str(levelrun), str(experiencegain)))
                    else:
                        util.sendmessage(messages.dungeon_good_run(username, str(round(normalrunquality*0.01, 2)), str(levelrun), str(experiencegain)))
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
                    time.sleep(1)
                    util.sendmessage(messages.user_level_up(username, str(user['user_level'] + 1)))
            else:
                db(opt.USERS).update_one(username, { '$inc': { 'dungeon_losses': 1 } })
                db(opt.GENERAL).update_one(0, { '$inc': { 'total_losses': 1 } })
                util.sendmessage(messages.dungeon_failed(username, str(levelrun)))
            db(opt.USERS).update_one(username, { '$inc': { 'dungeons': 1 } })
            db(opt.GENERAL).update_one(0, { '$inc': { 'total_dungeons': 1 } })
        else:
            util.sendmessage(messages.dungeon_already_entered(username, str(datetime.timedelta(seconds=(int(user['next_entry']) - time.time()))).split('.')[0]))
    else:
        util.sendmessage(messages.you_not_registered(username))

def dungeonlvl():
    dungeon = db(opt.GENERAL).find_one_by_id(0)
    util.sendmessage(messages.dungeon_level(str(dungeon['dungeon_level'])))

def dungeonmaster():
    topuser = db(opt.USERS).find_one(sort=[('total_experience', -1)])
    if topuser:
        highestexperience = topuser['total_experience']
        numberoftopusers = db(opt.USERS).count_documents( {'total_experience': highestexperience} )
        if numberoftopusers == 1:
            thetopuser = db(opt.USERS).find_one( {'total_experience': highestexperience} )
            util.sendmessage(messages.dungeon_master(thetopuser['_id'], str(highestexperience)))
        else:
            util.sendmessage(messages.dungeon_masters(str(numberoftopusers), str(highestexperience)))
    else:
        util.sendmessage(messages.dungeon_no_master)

def dungeonstats():
    dungeon = db(opt.GENERAL).find_one_by_id(0)
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
    if dungeons is not 0:
        util.sendmessage(messages.dungeon_general_stats(str(dungeons), dungeonword, str(wins), winword, str(losses), loseword, str(round((((wins)/(dungeons))*100), 3))))
    else:
        util.sendmessage(messages.dungeon_general_stats(str(dungeons), dungeonword, str(wins), winword, str(losses), loseword, '0'))

def dungeonstatus():
    uptime = time.time()
    util.sendmessage(messages.dungeon_uptime(str(datetime.timedelta(seconds=(int(uptime - botstart))))))

def ping():
    util.sendmessage(messages.pong)

def register(username):
    user = db(opt.USERS).find_one_by_id(username)
    if user == None:
        db(opt.GENERAL).update_one(0, { '$inc': { 'dungeon_level': 1 } })
        db(opt.USERS).update_one(username, { '$set': schemes.USER }, upsert=True)
        dungeon = db(opt.GENERAL).find_one_by_id(0)
        util.sendmessage(messages.dungeon_level_up(str(dungeon['dungeon_level'])))
    else:
        util.sendmessage(messages.user_already_registered(username))

def userexperience(username, message):
    if message == '+xp' or message == 'exp':
        registered = util.checkuserregistered(username)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            util.sendmessage(messages.user_experience(username, str(user['total_experience'])))
    else:
        targetuser = re.search('(?:xp|exp) (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if targetuser.lower() == username.lower():
                registered = util.checkuserregistered(username)
                if registered:
                    user = db(opt.USERS).find_one_by_id(username)
                    util.sendmessage(messages.user_experience(username, str(user['total_experience'])))
            else:
                targetusername = re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE)
                target = db(opt.USERS).find_one_by_id(targetusername)
                if not util.checkusername(targetuser):
                    registered = util.checkuserregistered(username)
                    if registered:
                        user = db(opt.USERS).find_one_by_id(username)
                        util.sendmessage(messages.user_experience(username, str(user['total_experience'])))
                elif target:
                    util.sendmessage(messages.user_experience(target['_id'], str(target['total_experience'])))
                else:
                    util.sendmessage(messages.user_no_experience(username))

def userlevel(username, message):
    if message == '+lvl' or message == '+level':
        registered = util.checkuserregistered(username)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            util.sendmessage(messages.user_level(username, str(user['user_level']), str(user['current_experience']), str((((user['user_level']) + 1)**2)*100)))
    else:
        targetuser = re.search('(?:lvl|level) (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if targetuser.lower() == username.lower():
                registered = util.checkuserregistered(username)
                if registered:
                    user = db(opt.USERS).find_one_by_id(username)
                    util.sendmessage(messages.user_level(username, str(user['user_level']), str(user['current_experience']), str((((user['user_level']) + 1)**2)*100)))
            else:
                targetusername = re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE)
                target = db(opt.USERS).find_one_by_id(targetusername)
                if not util.checkusername(targetuser):
                    registered = util.checkuserregistered(username)
                    if registered:
                        user = db(opt.USERS).find_one_by_id(username)
                        util.sendmessage(messages.user_level(username, str(user['user_level']), str(user['current_experience']), str((((user['user_level']) + 1)**2)*100)))
                elif target:
                    util.sendmessage(messages.user_level(target['_id'], str(target['user_level']), str(user['current_experience']), str((((user['user_level']) + 1)**2)*100)))
                else:
                    util.sendmessage(messages.user_no_level(username))

def winrate(username, message):
    if message == '+winrate':
        registered = util.checkuserregistered(username)
        if registered:
            user = db(opt.USERS).find_one_by_id(username)
            if user['dungeons'] == 0:
                util.sendmessage(messages.you_no_entered_dungeons(username))
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
                util.sendmessage(messages.user_stats(username, str(wins), winword, str(losses), loseword, str(round((((wins)/(dungeons))*100), 3))))
    else:
        targetuser = re.search('winrate (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if (targetuser.lower() == username.lower()) or not util.checkusername(targetuser):
                registered = util.checkuserregistered(username)
                if registered:
                    user = db(opt.USERS).find_one_by_id(username)
                    if user['dungeons'] == 0:
                        util.sendmessage(messages.you_no_entered_dungeons(username))
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
                        util.sendmessage(messages.user_stats(username, str(wins), winword, str(losses), loseword, str(round((((wins)/(dungeons))*100), 3))))
            else:
                targetusername = re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE)
                registered = util.checkuserregistered(username, targetusername)
                if registered:
                    target = db(opt.USERS).find_one_by_id(targetusername)
                    if target is not None and target['dungeons'] is 0:
                        util.sendmessage(messages.user_no_entered_dungeons(username))
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
                        util.sendmessage(messages.user_stats(target['_id'], str(wins), winword, str(losses), loseword, str(round((((wins)/(dungeons))*100), 3))))
