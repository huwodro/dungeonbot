import re
import time
import threading

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
        except requests.ConnectionError:
            print('HTTP ERROR: ConnectionError')
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

while True:
    try:
        resp = emoji.demojize(util.sock.recv(2048).decode('utf-8'))
    except Exception as e:
        # print(e)
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
