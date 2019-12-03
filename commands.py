import datetime
import db
import emoji
import random
import re
import time
import utility as util

botstart = time.time()

### User Commands ###

def commands():
    return emoji.emojize(':memo:', use_aliases=True) + 'Commands: +register | +enterdungeon | +dungeonlvl | +lvl | +xp | +winrate | +dungeonmaster | +dungeonstats | +dungeonstatus'

def enterdungeon(username, message):
    if db.usercollection.count_documents({'_id': username}, limit = 1) != 0:
        if int((db.usercollection.find_one( {'_id': username})['dungeonTimeout']) - (time.time() - (db.usercollection.find_one( {'_id': username})['enteredTime']))) < 0:
            util.opendungeon(username)
        if db.usercollection.find_one( {'_id': username})['entered'] == 0:
            dungeonlevel = db.generalcollection.find_one( {'_id': 0 } )['dungeonlevel']
            userlevel = db.usercollection.find_one( {'_id': username})['userlevel']

            if message == '+enterdungeon':
                if userlevel > dungeonlevel:
                    levelrun = dungeonlevel
                    successrate = 65-((dungeonlevel-userlevel)*7)
                    experiencegain = int(100*dungeonlevel)*(1.2**(dungeonlevel-userlevel))
                    dungeontimeout = 600-(60*(userlevel-dungeonlevel))
                else:
                    levelrun = userlevel
                    successrate = 65
                    experiencegain = int(100*userlevel)
                    dungeontimeout = 600
            else:
                targetnumber = re.search('enterdungeon (.*)', message)
                if targetnumber:
                    targetnumber = targetnumber.group(1)
                    if targetnumber.isnumeric() == False:
                        if userlevel > dungeonlevel:
                            levelrun = dungeonlevel
                            successrate = 65-((dungeonlevel-userlevel)*7)
                            experiencegain = int(100*dungeonlevel)*(1.2**(dungeonlevel-userlevel))
                            dungeontimeout = 600-(60*(userlevel-dungeonlevel))
                        else:
                            levelrun = userlevel
                            successrate = 65
                            experiencegain = int(100*userlevel)
                            dungeontimeout = 600
                    elif int(targetnumber) <= 0:
                        return username + ", you can't enter dungeons below level [1]" + emoji.emojize(' :crossed_swords:', use_aliases=True)
                    elif int(targetnumber) > dungeonlevel:
                        return username + ', the Dungeon is currently level [' + str(dungeonlevel) + "] - You can't venture beyond this level yet" + emoji.emojize(' :crossed_swords:', use_aliases=True)
                    elif int(targetnumber) > (userlevel + 5):
                        return username + ', the Dungeon [' + targetnumber + "] is too high level for you to enter. You can't enter dungeons that exceed 5 levels above your own" + emoji.emojize(' :crossed_swords:', use_aliases=True)
                    else:
                        levelrun = int(targetnumber)
                        successrate = 65-((int(targetnumber)-userlevel)*7)
                        experiencegain = (100*int(targetnumber))*(1.2**(int(targetnumber)-userlevel))
                        dungeontimeout = 600-(60*(userlevel-int(targetnumber)))

            dungeonsuccess = random.randint(1, 101)
            db.usercollection.update_one( {'_id': username}, {'$set': {'entered': 1} } )
            db.usercollection.update_one( {'_id': username}, {'$set': {'dungeonTimeout': dungeontimeout} } )
            db.usercollection.update_one( {'_id': username}, {'$set': {'enteredTime': time.time()} } )

            if dungeonsuccess <= successrate:
                rarerunquality = random.randint(1, 101)
                if rarerunquality <= 10:
                    experiencegain = int(experiencegain*0.5)
                    db.usercollection.update_one( {'_id': username}, {'$inc': { 'total_experience': experiencegain } } )
                    db.usercollection.update_one( {'_id': username}, {'$inc': { 'current_experience': experiencegain } } )
                    db.generalcollection.update_one( {'_id': 0}, {'$inc': { 'total_experience': experiencegain } } )
                    util.queuemessage(username + ' | Very Bad Run [x0.5] - You beat the dungeon level [' + str(levelrun) + '] - Experience Gained: ' + str(experiencegain) + ' PogChamp')
                elif rarerunquality >= 90:
                    experiencegain = int(experiencegain*1.5)
                    db.usercollection.update_one( {'_id': username}, {'$inc': { 'total_experience': experiencegain } } )
                    db.usercollection.update_one( {'_id': username}, {'$inc': { 'current_experience': experiencegain } } )
                    db.generalcollection.update_one( {'_id': 0}, {'$inc': { 'total_experience': experiencegain } } )
                    util.queuemessage(username + ' | Very Good Run [x1.5] - You beat the dungeon level [' + str(levelrun) + '] - Experience Gained: ' + str(experiencegain) + ' PogChamp')
                else:
                    normalrunquality = random.randint(75,126)
                    experiencegain = int(experiencegain*normalrunquality*0.01)
                    if normalrunquality < 100:
                        util.queuemessage(username + ' | Bad Run [x' + str(round(normalrunquality*0.01, 2)) + '] - You beat the dungeon level [' + str(levelrun) + '] - Experience Gained: ' + str(experiencegain) + ' PogChamp')
                    else:
                        util.queuemessage(username + ' | Good Run [x' + str(round(normalrunquality*0.01, 2)) + '] - You beat the dungeon level [' + str(levelrun) + '] - Experience Gained: ' + str(experiencegain) + ' PogChamp')
                    db.usercollection.update_one( {'_id': username}, {'$inc': { 'total_experience': experiencegain } } )
                    db.usercollection.update_one( {'_id': username}, {'$inc': { 'current_experience': experiencegain } } )
                    db.generalcollection.update_one( {'_id': 0}, {'$inc': { 'total_experience': experiencegain } } )
                db.usercollection.update_one( {'_id': username}, {'$inc': { 'dungeon_wins': 1 } } )
                db.generalcollection.update_one( {'_id': 0}, {'$inc': { 'total_wins': 1 } } )
                if (((userlevel+1)**2)*100) - db.usercollection.find_one( {'_id': username})['current_experience'] <= 0:
                    while (((db.usercollection.find_one( {'_id': username})['userlevel']+1)**2)*100) - db.usercollection.find_one( {'_id': username})['current_experience'] <= 0:
                        db.usercollection.update_one( {'_id': username}, {'$inc': { 'userlevel': 1 } } )
                        db.usercollection.update_one( {'_id': username}, {'$inc': { 'current_experience': -(((db.usercollection.find_one( {'_id': username})['userlevel'])**2)*100) } } )
                    util.queuemessage(username + ' just leveled up! Level - [' + str(db.usercollection.find_one( {'_id': username})['userlevel']) + '] PogChamp')
            else:
                db.usercollection.update_one( {'_id': username}, {'$inc': { 'dungeon_losses': 1 } } )
                db.generalcollection.update_one( {'_id': 0}, {'$inc': { 'total_losses': 1 } } )
                util.queuemessage(username + ', you failed to beat the dungeon level [' + str(levelrun) + '] - No experience gained FeelsBadMan')
            db.usercollection.update_one( {'_id': username}, {'$inc': { 'dungeons': 1 } } )
            db.generalcollection.update_one( {'_id': 0}, {'$inc': { 'total_dungeons': 1 } } )
        else:
            return username + ', you have already entered the dungeon recently, ' + str(datetime.timedelta(seconds=(int((db.usercollection.find_one( {'_id': username})['dungeonTimeout']) - (time.time() - (db.usercollection.find_one( {'_id': username})['enteredTime'])))))) + ' left until you can enter again!' + emoji.emojize(' :hourglass:', use_aliases=True)
    else:
        return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:')

def dungeonlvl():
    return emoji.emojize(':shield:', use_aliases=True) + ' Dungeon Level: [' + str(db.generalcollection.find_one( {'_id': 0} )['dungeonlevel']) + ']'

def dungeonmaster():
    topuser = db.usercollection.find_one(sort=[('total_experience', -1)])
    if topuser:
        highestexperience = topuser['total_experience']
        numberoftopusers = db.usercollection.count_documents( {'total_experience': highestexperience} )
        if numberoftopusers == 1:
            return str(db.usercollection.find_one( {'total_experience': highestexperience} )['_id']) + ' is the current Dungeon Master with ' + str(highestexperience) + ' experience' + emoji.emojize(' :crown:', use_aliases=True)
        else:
            return 'There are ' + str(numberoftopusers) + ' users with ' + str(highestexperience) + ' experience, no one is currently Dungeon Master FeelsBadMan'
    else:
        return 'There is currently no Dungeon Master FeelsBadMan'

def dungeonstats():
    dungeons = db.generalcollection.find_one( {'_id': 0} )['total_dungeons']
    wins = db.generalcollection.find_one( {'_id': 0} )['total_wins']
    losses = db.generalcollection.find_one( {'_id': 0} )['total_losses']
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
        return 'General Dungeon Stats: ' + str(dungeons) + dungeonword + ' / ' + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)
    else:
        return 'General Dungeon Stats: ' + str(dungeons) + dungeonword + ' / ' + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + '0% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)

def dungeonstatus():
    uptime = time.time()
    return 'Dungeon Uptime: ' + str(datetime.timedelta(seconds=(int(uptime - botstart)))) + emoji.emojize(' :stopwatch:', use_aliases=True)

def ping():
    return 'Dungeon Bot MrDestructoid For a list of commands, type +commands'

def register(username):
    if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
        db.generalcollection.update_one( {'_id': 0}, {'$inc': {'dungeonlevel': 1} } )
        db.usercollection.insert_one( {'_id': username, 'userlevel': 1, 'total_experience': 0, 'current_experience': 0, 'dungeons': 0, 'dungeon_wins': 0, 'dungeon_losses': 0, 'entered': 0, 'enteredTime': 0, 'dungeonTimeout': 0} )
        util.queuemessage('DING PogChamp Dungeon Level [' + str(db.generalcollection.find_one( {'_id': 0 } )['dungeonlevel']) + ']')
    else:
        return username + ', you are already a registered user! 4Head'

def userexperience(username, message):
    if message == '+xp' or message == 'exp':
        if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
            return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
        else:
            return username + "'s total experience: " + str(int(db.usercollection.find_one( {'_id': username } )['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True)
    else:
        targetuser = re.search('(?:xp|exp) (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if targetuser.lower() == username.lower():
                if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
                    return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
                else:
                    return username + "'s total experience: " + str(int(db.usercollection.find_one( {'_id': username } )['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True)
            else:
                if not util.checkusername(targetuser):
                    if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
                        return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
                    else:
                        return username + "'s total experience: " + str(int(db.usercollection.find_one( {'_id': username } )['total_experience'])) + emoji.emojize(' :diamonds:', use_aliases=True)
                elif db.usercollection.count_documents( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) }, limit = 1) == 0:
                    return username + ', no experience found for that user!' + emoji.emojize(' :warning:', use_aliases=True)
                else:
                    return str(db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['_id']) + '\'s total experience: ' + str(db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['total_experience']) + emoji.emojize(' :diamonds:', use_aliases=True)

def userlevel(username, message):
    if message == '+lvl' or message == '+level':
        if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
            return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
        else:
            return username + "'s current level: [" + str(db.usercollection.find_one( {'_id': username } )['userlevel']) + '] - XP (' + str(int(db.usercollection.find_one( {'_id': username } )['current_experience'])) + ' / ' + str((((db.usercollection.find_one( {'_id': username } )['userlevel']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True)
    else:
        targetuser = re.search('(?:lvl|level) (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if targetuser.lower() == username.lower():
                if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
                    return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
                else:
                    return username + "'s current level: [" + str(db.usercollection.find_one( {'_id': username } )['userlevel']) + '] - XP (' + str(int(db.usercollection.find_one( {'_id': username } )['current_experience'])) + ' / ' + str((((db.usercollection.find_one( {'_id': username } )['userlevel']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True)
            else:
                if not util.checkusername(targetuser):
                    if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
                        return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
                    else:
                        return username + "'s current level: [" + str(db.usercollection.find_one( {'_id': username } )['userlevel']) + '] - XP (' + str(int(db.usercollection.find_one( {'_id': username } )['current_experience'])) + ' / ' + str((((db.usercollection.find_one( {'_id': username } )['userlevel']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True)
                elif db.usercollection.count_documents( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) }, limit = 1) == 0:
                    return username + ', no level found for that user!' + emoji.emojize (' :warning:')
                else:
                    return str(db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['_id']) + '\'s current level: [' + str(db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['userlevel']) + '] - XP (' + str(db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['current_experience']) + ' / ' + str((((db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['userlevel']) + 1)**2)*100) + ')' + emoji.emojize(' :diamonds:', use_aliases=True)

def winrate(username, message):
    if message == '+winrate':
        if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
            return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
        elif db.usercollection.find_one( {'_id': username } )['dungeons'] == 0:
            return username + ", you haven't entered any dungeons NotLikeThis"
        else:
            dungeons = db.usercollection.find_one( {'_id': username } )['dungeons']
            wins = db.usercollection.find_one( {'_id': username } )['dungeon_wins']
            losses = db.usercollection.find_one( {'_id': username } )['dungeon_losses']

            if wins == 1:
                winword = ' Win'
            else:
                winword = ' Wins'
            if losses == 1:
                loseword = ' Loss'
            else:
                loseword = ' Losses'
            return username + "'s winrate: " + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)
    else:
        targetuser = re.search('winrate (.*)', message)
        if targetuser:
            targetuser = targetuser.group(1)
            if targetuser.lower() == username.lower():
                if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
                    return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
                elif db.usercollection.find_one( {'_id': username } )['dungeons'] == 0:
                    return username + ", you haven't entered any dungeons NotLikeThis"
                else:
                    dungeons = db.usercollection.find_one( {'_id': username} )['dungeons']
                    wins = db.usercollection.find_one( {'_id': username} )['dungeon_wins']
                    losses = db.usercollection.find_one( {'_id': username} )['dungeon_losses']

                    if wins == 1:
                        winword = ' Win'
                    else:
                        winword = ' Wins'
                    if losses == 1:
                        loseword = ' Loss'
                    else:
                        loseword = ' Losses'
                    return username + "'s winrate: " + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)
            else:
                if not util.checkusername(targetuser):
                    if db.usercollection.count_documents({'_id': username}, limit = 1) == 0:
                        return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)
                    elif db.usercollection.find_one( {'_id': username } )['dungeons'] == 0:
                        return username + ", you haven't entered any dungeons NotLikeThis"
                    else:
                        dungeons = db.usercollection.find_one( {'_id': username} )['dungeons']
                        wins = db.usercollection.find_one( {'_id': username} )['dungeon_wins']
                        losses = db.usercollection.find_one( {'_id': username} )['dungeon_losses']

                        if wins == 1:
                            winword = ' Win'
                        else:
                            winword = ' Wins'
                        if losses == 1:
                            loseword = ' Loss'
                        else:
                            loseword = ' Losses'
                        return username + "'s winrate: " + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)
                elif db.usercollection.count_documents( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) }, limit = 1) == 0:
                    return username + ', that user is not registered!' + emoji.emojize(' :warning:', use_aliases=True)
                elif db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['dungeons'] == 0:
                    return username + ", that user hasn't entered any dungeons NotLikeThis"
                else:
                    dungeons = db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['dungeons']
                    wins = db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['dungeon_wins']
                    losses = db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['dungeon_losses']

                    if wins == 1:
                        winword = ' Win'
                    else:
                        winword = ' Wins'
                    if losses == 1:
                        loseword = ' Loss'
                    else:
                        loseword = ' Losses'
                    return str(db.usercollection.find_one( {'_id': re.compile('^' + re.escape(targetuser) + '$', re.IGNORECASE) } )['_id']) + '\'s winrate: ' + str(wins) + winword +' / ' + str(losses) + loseword + ' = ' + str((((wins)/(dungeons))*100)) + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)
