from collections import defaultdict
import math
import random
import re
import sys
import time
import threading
import traceback

import emoji
import requests

import auth
import utility as util
import commands as cmd
import database as opt
import schemes
import messages

db = opt.MongoDatabase
botprefix = '+'
global raidstart
raidstart = False
raidusers = []
usersbychannel = defaultdict(list)

util.start()

def livecheck():
    while True:
        onlinechannels = []
        headers = { 'Authorization': auth.bearer }
        params = []
        for channel in db.raw[opt.CHANNELS].find():
            tuple = ('user_login', channel['_id'])
            params.append(tuple)
        try:
            response = requests.get('https://api.twitch.tv/helix/streams', headers=headers, params=params).json()
        except:
            sys.stderr.write(traceback.format_exc() + '\n')
            sys.stderr.flush()
        else:
            for online in response['data']:
                onlinechannels.append(online['user_name'].lower())
            for channel in db.raw[opt.CHANNELS].find():
                if channel['_id'] in onlinechannels:
                    db(opt.CHANNELS).update_one(channel['_id'], { '$set': { 'online': 1 } }, upsert=True)
                else:
                    db(opt.CHANNELS).update_one(channel['_id'], { '$set': { 'online': 0 } }, upsert=True)

        time.sleep(auth.reconnect_timer)

livecheckthread = threading.Thread(target = livecheck)
livecheckthread.start()

def raidevent():
    time_to_join = 120
    message_interval = 30
    interval_range = time_to_join - message_interval
    while True:
        successrate = 0
        dungeon = db(opt.GENERAL).find_one_by_id(0)
        if int(dungeon['raid_time'] - time.time()) <= 0:
            raidlevel = random.randint(1, dungeon['dungeon_level']+1)
            global raidstart
            raidstart = True
            time.sleep(0.5)
            util.queuemessage(messages.raid_event_appear(str(raidlevel), str(time_to_join)), 1)
            time.sleep(message_interval)
            for i in range(interval_range, 0, -(message_interval)):
                util.queuemessage(messages.raid_event_countdown(str(i)), 1)
                time.sleep(message_interval)
            raidstart = False
            rand = random.randint(3600, 7200)
            db(opt.GENERAL).update_one(0, { '$set': { 'raid_time': time.time() + rand } }, upsert=True)
            if len(raidusers) == 0:
                util.queuemessage(messages.raid_event_no_users(), 1)
                continue
            elif len(raidusers) == 1:
                userWord = ' user'
            else:
                userWord = ' users'
            for user in raidusers:
                id = util.checkuserid(user[1])
                successrate += math.ceil(db(opt.USERS).find_one_by_id(id)['user_level'] / raidlevel * 150)
            util.queuemessage(messages.raid_event_start(str(len(raidusers)), userWord, str(successrate/10)), 1)
            time.sleep(3)
            raidsuccess = random.randint(1, 1001)
            if raidsuccess <= successrate:
                experiencegain = int(raidlevel**1.2 * 300 / len(raidusers))
                util.queuemessage(messages.raid_event_win(str(len(raidusers)), userWord, str(raidlevel), str(experiencegain)), 1)
                for user, channel in raidusers:
                    usersbychannel[user].append(channel)
                for channel in usersbychannel.items():
                    levelupusers = []
                    for user in channel[1]:
                        id = util.checkuserid(user)
                        db(opt.USERS).update_one(id, {'$inc': {
                            'total_experience': experiencegain,
                            'current_experience': experiencegain,
                            'raid_wins': 1,
                            'raids': 1
                        }})
                        if (((db(opt.USERS).find_one_by_id(id)['user_level']+1)**2)*100) - db(opt.USERS).find_one_by_id(id)['current_experience'] <= 0:
                            while (((db(opt.USERS).find_one_by_id(id)['user_level']+1)**2)*100) - db(opt.USERS).find_one_by_id(id)['current_experience'] <= 0:
                                db(opt.USERS).update_one(id, {'$inc': {
                                    'user_level': 1,
                                    'current_experience': -(((db(opt.USERS).find_one_by_id(id)['user_level']+1)**2)*100)
                                }})
                            levelupusers.append(user)
                    if levelupusers:
                        i = 1
                        for user in levelupusers[::5]:
                            util.queuemessage(messages.users_level_up(levelupusers[levelupusers.index(user):5*i]), 0, channel[0])
                            i += 1
                db(opt.GENERAL).update_one(0, {'$inc': {
                    'total_experience': experiencegain,
                    'total_raid_wins': 1
                }})
            else:
                util.queuemessage(messages.raid_event_failed(str(len(raidusers)), userWord, str(raidlevel)), 1)
                for user in raidusers:
                    id = util.checkuserid(user[0])
                    db(opt.USERS).update_one(id, {'$inc': {
                        'raid_losses': 1,
                        'raids': 1
                    }})
                db(opt.GENERAL).update_one(0, { '$inc': { 'total_raid_losses': 1 } })
            db(opt.GENERAL).update_one(0, { '$inc': { 'total_raids': 1 } })
            raidusers.clear()
            usersbychannel.clear()
        time.sleep(60)

raideventthread = threading.Thread(target = raidevent)
raideventthread.start()

while True:
    try:
        resp = emoji.demojize(util.sock.recv(2048).decode('utf-8'))
    except:
        util.sock.close()
        util.connect()
    else:
        if len(resp) == 0:
            util.sock.close()
            util.connect()

        if resp.startswith('PING'):
            util.pong()

        elif len(resp) > 0:
            username = re.search('display-name=(.+?);', resp)
            if username:
                username = username.group(1)
            channel = re.search('( PRIVMSG #(.+?) )', resp)
            if channel:
                channel = channel.group(2)
            message = re.search(':\B(.*)', resp)
            if message:
                message = message.group(1).strip()

                if message.startswith(botprefix) or message == '!bot' or message == '!huwobot':
                    params = message[1:].casefold().split(' ')

                    if db(opt.CHANNELS).find_one_by_id(channel)['online'] == 0:
                        try:
                            id = util.checkuserid(username)
                            user_cmdusetime = db(opt.USERS).find_one_by_id(id)['cmdusetime']
                        except:
                            user_cmdusetime = 0
                        user_cooldown = db(opt.CHANNELS).find_one_by_id(channel)['user_cooldown']
                        global_cmdusetime = db(opt.CHANNELS).find_one_by_id(channel)['cmdusetime']
                        global_cooldown = db(opt.CHANNELS).find_one_by_id(channel)['global_cooldown']
                        message_queued = db(opt.CHANNELS).find_one_by_id(channel)['message_queued']
                        if time.time() > global_cmdusetime + global_cooldown and time.time() > user_cmdusetime + user_cooldown and message_queued == 0:

                            if message == '!bot' or message == '!huwobot':
                                util.sendmessage(messages.bot_description, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'commands' or params[0] == 'help':
                                cmd.commands(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'enterdungeon' or params[0] == 'ed':
                                cmd.enterdungeon(username, message, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonlvl' or params[0] == 'dungeonlevel':
                                cmd.dungeonlvl(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonmaster' or params[0] == 'dm':
                                cmd.dungeonmaster(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonstats':
                                cmd.dungeonstats(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'raidstats':
                                cmd.raidstats(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonstatus' or params[0] == 'uptime':
                                cmd.dungeonstatus(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'ping':
                                util.sendmessage(messages.pong, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'register':
                                cmd.register(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'xp' or params[0] == 'exp':
                                try:
                                    cmd.userexperience(username, channel, params[1])
                                except IndexError:
                                    cmd.userexperience(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'lvl' or params[0] == 'level':
                                try:
                                    cmd.userlevel(username, channel, params[1])
                                except IndexError:
                                    cmd.userlevel(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'winrate' or params[0] == 'wr':
                                try:
                                    cmd.winrate(username, channel, params[1])
                                except IndexError:
                                    cmd.winrate(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'join':
                            if raidstart:
                                if not [user for user in raidusers if username in user]:
                                    id = util.checkuserid(username)
                                    user = db(opt.USERS).find_one_by_id(id)
                                    if user is not None and user.get('user_level') is not None:
                                        raidusers.append((channel, username))
                                    else:
                                        registerthread = threading.Thread(target = util.queuemessage, args=(messages.you_not_registered(username), 0, channel))
                                        registerthread.start()

                    if params[0] == 'suggest':
                        util.suggest(username, channel, message[len(params[0])+2:])

                    ### Admin Commands ###

                    if params[0] == 'text':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            modes = ['vgr', 'vbr', 'gr', 'br', 'fail']
                            try:
                                if params[1] in modes:
                                    util.dungeontext(params[1], message[len(params[0])+len(params[1])+2:])
                                else:
                                    util.queuemessage(messages.add_text_error, 0, channel)
                            except IndexError:
                                util.queuemessage(messages.add_text_error, 0, channel)

                    if params[0] == 'cs':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            try:
                                util.checksuggestion(username, channel, int(params[1]))
                            except:
                                suggestions = []
                                for suggestion in db.raw[opt.SUGGESTIONS].find():
                                    suggestions.append(suggestion['_id'])
                                if suggestions:
                                    util.whisper(username, messages.list_suggestions(suggestions), channel)
                                else:
                                    util.whisper(username, messages.no_suggestions, channel)

                    if params[0] == 'rs':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            try:
                                util.removesuggestion(username, channel, int(params[1]))
                            except IndexError:
                                util.whisper(username, messages.remove_suggestion_usage_error, channel)
                            except ValueError as e:
                                util.whisper(username, messages.error_message(e), channel)

                    if params[0] == 'add':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            try:
                                util.joinchannel(channel, params[1], float(params[2]), float(params[3]))
                            except IndexError:
                                if len(params) == 3:
                                    util.joinchannel(channel, params[1], float(params[2]), 0)
                                elif len(params) == 2:
                                    util.joinchannel(channel, params[1], 2.5, 0)
                                else:
                                    util.queuemessage(messages.add_channel_error, 0, channel)
                            except ValueError as e:
                                util.queuemessage(messages.error_message(e), 0, channel)

                    if params[0] == 'part':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None:
                            if admin.get('admin') == 1:
                                try:
                                    util.partchannel(params[1])
                                except IndexError:
                                    util.queuemessage(messages.part_channel_error, 0, channel)
                            elif admin.get('moderator') == 1:
                                try:
                                    if params[1] == username.casefold():
                                        util.partchannel(params[1])
                                except IndexError:
                                    util.partchannel(username.casefold())

                    if params[0] == 'cd' or params[0] == 'cooldown':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            try:
                                util.setcooldown(params[1], params[2], float(params[3]), channel)
                            except IndexError:
                                util.queuemessage(messages.set_cooldown_error, 0, channel)
                            except ValueError as e:
                                util.queuemessage(messages.error_message(e), 0, channel)

                    if params[0] == 'channels':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            util.listchannels(channel)

                    if params[0] == 'eval':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            util.runeval(channel, message[len(params[0])+2:])

                    if params[0] == 'exec':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            util.runexec(channel, message[len(params[0])+2:])

                    if params[0] == 'tag':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            try:
                                util.usertag(channel, params[1], params[2])
                            except IndexError as e:
                                util.queuemessage(messages.tag_error, 0, channel)

                    if params[0] == 'resetcd':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            util.resetcd(channel)

                    if params[0] == 'restart':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin.get('admin') == 1:
                            util.restart()
