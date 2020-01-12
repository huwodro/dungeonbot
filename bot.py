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
db(opt.CHANNELS).update_one(auth.defaultchannel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
messagedelay = 2.5
botprefix = '+'
global raidstart
raidstart = False
raidusers = []

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

util.start()

def raidevent():
    while True:
        successrate = 0
        dungeon = db(opt.GENERAL).find_one_by_id(0)
        if int(dungeon['raid_time'] - time.time()) <= 0:
            raidlevel = random.randint(1, dungeon['dungeon_level']+1)
            global raidstart
            raidstart = True
            util.queuemessage(messages.raid_event_appear(str(raidlevel)), 1)
            time.sleep(15)
            for i in range(45, 0, -15):
                util.queuemessage(messages.raid_event_countdown(str(i)), 1)
                time.sleep(15)
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
                successrate += math.ceil(db(opt.USERS).find_one_by_id(user[0])['user_level'] / raidlevel * 100)
            util.queuemessage(messages.raid_event_start(str(len(raidusers)), userWord, str(successrate/10)), 1)
            time.sleep(3)
            raidsuccess = random.randint(1, 1001)
            if raidsuccess <= successrate:
                experiencegain = int(raidlevel**1.2 * 200 / len(raidusers))
                util.queuemessage(messages.raid_event_win(str(len(raidusers)), userWord, str(raidlevel), str(experiencegain)), 1)
                for user in raidusers:
                    db(opt.USERS).update_one(user[0], {'$inc': {
                        'total_experience': experiencegain,
                        'current_experience': experiencegain,
                        'raid_wins': 1
                    }})
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
                    db(opt.USERS).update_one(user[0], { '$inc': { 'raid_losses': 1 } })
                db(opt.GENERAL).update_one(0, { '$inc': { 'total_raid_losses': 1 } })
            db(opt.USERS).update_one(user[0], { '$inc': { 'raids': 1 } })
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

                if message.startswith(botprefix):
                    params = message[1:].casefold().split(' ')

                    if db(opt.CHANNELS).find_one_by_id(channel)['online'] == 0:
                        cmdusetime = db(opt.CHANNELS).find_one_by_id(channel)['cmdusetime']
                        if time.time() > cmdusetime + messagedelay and util.messagequeue.empty():

                            if params[0] == 'commands' or params[0] == 'help':
                                cmd.commands(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'enterdungeon' or params[0] == 'ed':
                                cmd.enterdungeon(username, message, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonlvl' or params[0] == 'dungeonlevel':
                                cmd.dungeonlvl(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonmaster' or params[0] == 'dm':
                                cmd.dungeonmaster(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonstats':
                                cmd.dungeonstats(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'raidstats':
                                cmd.raidstats(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'dungeonstatus':
                                cmd.dungeonstatus(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'ping':
                                cmd.ping(channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'register':
                                cmd.register(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'xp' or params[0] == 'exp':
                                try:
                                    cmd.userexperience(username, channel, params[1])
                                except IndexError:
                                    cmd.userexperience(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'lvl' or params[0] == 'level':
                                try:
                                    cmd.userlevel(username, channel, params[1])
                                except IndexError:
                                    cmd.userlevel(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                            if params[0] == 'winrate':
                                try:
                                    cmd.winrate(username, channel, params[1])
                                except IndexError:
                                    cmd.winrate(username, channel)
                                db(opt.CHANNELS).update_one(channel, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'join':
                            if raidstart:
                                if username not in dict(raidusers):
                                    user = db(opt.USERS).find_one_by_id(username)
                                    if user is not None:
                                        raidusers.append((username, channel))
                                    else:
                                        util.queuemessage(messages.you_not_registered(username), 0, channel)

                    if params[0] == 'add':
                        try:
                            util.joinchannel(username, channel, params[1])
                        except IndexError as e:
                            util.queuemessage(messages.channel_error(), channel)

                    if params[0] == 'part':
                        try:
                            util.partchannel(username, params[1])
                        except IndexError as e:
                            util.queuemessage(messages.channel_error(), channel)

                    if params[0] == 'channels':
                        util.listchannels(username, channel)

                    if params[0] == 'eval':
                        util.runeval(username, channel, message[6:])

                    if params[0] == 'exec':
                        util.runexec(username, channel, message[6:])

                    if params[0] == 'tag':
                        try:
                            util.usertag(username, channel, params[1], params[2])
                        except IndexError as e:
                            util.queuemessage(messages.tag_error(), channel)

                    if params[0] == 'resetcd':
                        util.resetcd(username, channel)

                    if params[0] == 'restart':
                        util.restart(username)
