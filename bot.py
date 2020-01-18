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

util.start()

def livecheck():
    while True:
        onlinechannels = []
        headers = { 'Client-ID': auth.clientID }
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
                successrate += math.ceil(db(opt.USERS).find_one_by_id(user[0])['user_level'] / raidlevel * 150)
            util.queuemessage(messages.raid_event_start(str(len(raidusers)), userWord, str(successrate/10)), 1)
            time.sleep(3)
            raidsuccess = random.randint(1, 1001)
            if raidsuccess <= successrate:
                experiencegain = int(raidlevel**1.2 * 250 / len(raidusers))
                util.queuemessage(messages.raid_event_win(str(len(raidusers)), userWord, str(raidlevel), str(experiencegain)), 1)
                for user in raidusers:
                    db(opt.USERS).update_one(user[0], {'$inc': {
                        'total_experience': experiencegain,
                        'current_experience': experiencegain,
                        'raid_wins': 1,
                        'raids': 1
                    }})
                    if (((db(opt.USERS).find_one_by_id(user[0])['user_level']+1)**2)*100) - db(opt.USERS).find_one_by_id(user[0])['current_experience'] <= 0:
                        while (((db(opt.USERS).find_one_by_id(user[0])['user_level']+1)**2)*100) - db(opt.USERS).find_one_by_id(user[0])['current_experience'] <= 0:
                            db(opt.USERS).update_one(user[0], {'$inc': {
                                'user_level': 1,
                                'current_experience': -(((db(opt.USERS).find_one_by_id(user[0])['user_level']+1)**2)*100)
                            }})
                        util.queuemessage(messages.user_level_up(user[0], str(db(opt.USERS).find_one_by_id(user[0])['user_level'])), 0, user[1])
                db(opt.GENERAL).update_one(0, {'$inc': {
                    'total_experience': experiencegain,
                    'total_raid_wins': 1
                }})
            else:
                util.queuemessage(messages.raid_event_failed(str(len(raidusers)), userWord, str(raidlevel)), 1)
                for user in raidusers:
                    db(opt.USERS).update_one(user[0], {'$inc': {
                        'raid_losses': 1,
                        'raids': 1
                    }})
                db(opt.GENERAL).update_one(0, { '$inc': { 'total_raid_losses': 1 } })
            db(opt.GENERAL).update_one(0, { '$inc': { 'total_raids': 1 } })
            raidusers.clear()
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

        elif resp.startswith(':tmi.twitch.tv PONG'):
            channel = re.search('\s:(.*)', resp)
            if channel:
                channel = channel.group(1)
            latency = round(((time.time() - ping_time)*1000), 2)
            util.sendmessage(messages.pong(str(latency)), channel)

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
                            user_cmdusetime = db(opt.USERS).find_one_by_id(username)['cmdusetime']
                        except:
                            user_cmdusetime = 0
                        user_cooldown = db(opt.CHANNELS).find_one_by_id(channel)['user_cooldown']
                        global_cmdusetime = db(opt.CHANNELS).find_one_by_id(channel)['cmdusetime']
                        global_cooldown = db(opt.CHANNELS).find_one_by_id(channel)['global_cooldown']
                        if time.time() > global_cmdusetime + global_cooldown and time.time() > user_cmdusetime + user_cooldown:

                            if message == '!bot' or message == '!huwobot':
                                util.sendmessage(messages.bot_description, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'commands' or params[0] == 'help':
                                cmd.commands(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'enterdungeon' or params[0] == 'ed':
                                cmd.enterdungeon(username, message, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonlvl' or params[0] == 'dungeonlevel':
                                cmd.dungeonlvl(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonmaster' or params[0] == 'dm':
                                cmd.dungeonmaster(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonstats':
                                cmd.dungeonstats(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'raidstats':
                                cmd.raidstats(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonstatus' or params[0] == 'uptime':
                                cmd.dungeonstatus(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'ping':
                                ping_time = time.time()
                                util.sock.send(('PING ' + channel + '\r\n').encode('utf-8'))
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'register':
                                cmd.register(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'xp' or params[0] == 'exp':
                                try:
                                    cmd.userexperience(username, channel, params[1])
                                except IndexError:
                                    cmd.userexperience(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'lvl' or params[0] == 'level':
                                try:
                                    cmd.userlevel(username, channel, params[1])
                                except IndexError:
                                    cmd.userlevel(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'winrate':
                                try:
                                    cmd.winrate(username, channel, params[1])
                                except IndexError:
                                    cmd.winrate(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                                db(opt.USERS).update_one(username, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'join':
                            if raidstart:
                                if username not in dict(raidusers):
                                    user = db(opt.USERS).find_one_by_id(username)
                                    if user is not None:
                                        raidusers.append((username, channel))
                                    else:
                                        util.queuemessage(messages.you_not_registered(username), 0, channel)

                    if params[0] == 'suggest':
                        util.suggest(username, channel, message[len(params[0])+2:])

                    ### Admin Commands ###

                    if params[0] == 'cs':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            try:
                                util.checksuggestion(username, channel, int(params[1]))
                            except:
                                suggestion = db(opt.SUGGESTIONS).find_one(sort=[('_id', 1)])
                                if suggestion is not None:
                                    id = suggestion['_id']
                                    util.checksuggestion(username, channel, int(id))
                                else:
                                    util.whisper(username, messages.no_suggestions, channel)

                    if params[0] == 'rs':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            try:
                                util.removesuggestion(username, channel, int(params[1]))
                            except IndexError:
                                util.whisper(username, messages.remove_suggestion_usage_error, channel)
                            except ValueError as e:
                                util.whisper(username, messages.error_message(e), channel)

                    if params[0] == 'add':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
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
                        if admin is not None and admin['admin'] == 1:
                            try:
                                util.partchannel(params[1])
                            except IndexError as e:
                                util.queuemessage(messages.channel_error(), 0, channel)

                    if params[0] == 'cd' or params[0] == 'cooldown':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            try:
                                util.setcooldown(params[1], params[2], float(params[3]))
                            except IndexError:
                                util.queuemessage(messages.set_cooldown_error, 0, channel)
                            except ValueError as e:
                                util.queuemessage(messages.error_message(e), 0, channel)

                    if params[0] == 'channels':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            util.listchannels(channel)

                    if params[0] == 'eval':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            util.runeval(channel, message[len(params[0])+2:])

                    if params[0] == 'exec':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            util.runexec(channel, message[len(params[0])+2:])

                    if params[0] == 'tag':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            try:
                                util.usertag(channel, params[1], params[2])
                            except IndexError as e:
                                util.queuemessage(messages.tag_error, 0, channel)

                    if params[0] == 'resetcd':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            util.resetcd(channel)

                    if params[0] == 'restart':
                        admin = db(opt.TAGS).find_one_by_id(username)
                        if admin is not None and admin['admin'] == 1:
                            util.restart()
