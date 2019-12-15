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

db = opt.MongoDatabase
cmdusetime = time.time()
messagedelay = 2.5
botprefix = '+'

def livecheck():
    while True:
        headers = { 'Client-ID': auth.clientID }
        params = (('user_login', auth.channelname),)
        response = requests.get('https://api.twitch.tv/helix/streams', headers=headers, params=params).json()
        if not response['data']:
            db(opt.GENERAL).update_one(0, { '$set': { 'open': 1 } })
        else:
            db(opt.GENERAL).update_one(0, { '$set': { 'open': 0 } })
        time.sleep(5)

livecheckthread = threading.Thread(target = livecheck)
livecheckthread.start()

util.start()

while True:
    resp = emoji.demojize(util.sock.recv(2048).decode('utf-8'))

    if len(resp) == 0:
        util.connect()

    elif resp.startswith('PING'):
        util.pong()

    elif len(resp) > 0:
        username = re.search('display-name=(.+?);', resp)
        if username:
            username = username.group(1)
        message = re.search(r':(.*)\s:(.*)', resp)
        if message:
            message = message.group(2).strip()

            if message.startswith(botprefix):
                params = message[1:].split(' ')

                if db(opt.GENERAL).find_one_by_id(0)['open'] == 1:
                    if time.time() > cmdusetime + messagedelay and util.messagequeue.empty():

                        if params[0] == 'commands' or params[0] == 'help':
                            cmd.commands()
                            cmdusetime = time.time()

                        if params[0] == 'enterdungeon' or params[0] == 'ed':
                            cmd.enterdungeon(username, message)
                            cmdusetime = time.time()

                        if params[0] == 'dungeonlvl' or params[0] == 'dungeonlevel':
                            cmd.dungeonlvl()
                            cmdusetime = time.time()

                        if params[0] == 'dungeonmaster' or params[0] == 'dm':
                            cmd.dungeonmaster()
                            cmdusetime = time.time()

                        if params[0] == 'dungeonstats':
                            cmd.dungeonstats()
                            cmdusetime = time.time()

                        if params[0] == 'dungeonstatus':
                            cmd.dungeonstatus()
                            cmdusetime = time.time()

                        if params[0] == 'ping':
                            cmd.ping()
                            cmdusetime = time.time()

                        if params[0] == 'register':
                            cmd.register(username)
                            cmdusetime = time.time()

                        if params[0] == 'xp' or params[0] == 'exp':
                            try:
                                cmd.userexperience(username, params[1])
                            except IndexError:
                                cmd.userexperience(username)
                            cmdusetime = time.time()

                        if params[0] == 'lvl' or params[0] == 'level':
                            try:
                                cmd.userlevel(username, params[1])
                            except IndexError:
                                cmd.userlevel(username)
                            cmdusetime = time.time()

                        if params[0] == 'winrate':
                            try:
                                cmd.winrate(username, params[1])
                            except IndexError:
                                cmd.winrate(username)
                            cmdusetime = time.time()

                if params[0] == 'eval':
                    util.runeval(username, message[6:])

                if params[0] == 'exec':
                    util.runexec(username, message[6:])

                if params[0] == 'tag':
                    try:
                        util.usertag(username, params[1], params[2])
                    except IndexError as e:
                        util.queuemessage(emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +tag <user> <role>')

                if params[0] == 'resetcd':
                    util.resetcd(username)

                if params[0] == 'restart':
                    util.restart(username)
