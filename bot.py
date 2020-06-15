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
bot_prefix = '+'
raid_users = []
users_by_channel = defaultdict(list)

message_regex = re.compile('MSG[^:]*:(.*)')
channel_regex = re.compile('MSG #(.+?) ')
user_regex = re.compile('user-id=(.+?);')
name_regex = re.compile('name=(.+?);')
err_name_regex = re.compile(':(.+?)!')

util.start()

def live_check():
    while True:
        online_channels = {}
        headers = { 'Authorization': auth.bearer, 'Client-ID': auth.clientID }
        params = []
        for channel in db.raw[opt.CHANNELS].find():
            tuple = ('user_id', channel['_id'])
            params.append(tuple)
        try:
            response = requests.get('https://api.twitch.tv/helix/streams', headers=headers, params=params).json()
        except:
            sys.stderr.write(traceback.format_exc() + '\n')
            sys.stderr.flush()
        else:
            for online in response['data']:
                online_channels[online['user_id']] = online['user_name'].lower()
            for channel in db.raw[opt.CHANNELS].find():
                if channel['_id'] in online_channels:
                    db(opt.CHANNELS).update_one(channel['_id'], {'$set': { 'online': 1 } }, upsert=True)
                else:
                    db(opt.CHANNELS).update_one(channel['_id'], { '$set': { 'online': 0 } }, upsert=True)

        time.sleep(auth.reconnect_timer)

live_check_thread = threading.Thread(target = live_check)
live_check_thread.start()

def raid_event():
    time_to_join = 120
    message_interval = 30
    interval_range = time_to_join - message_interval
    while True:
        success_rate = 0
        dungeon = db(opt.GENERAL).find_one_by_id(0)
        if int(dungeon['raid_time'] - time.time()) <= 0:
            raid_level = random.randint(1, dungeon['dungeon_level']+1)
            db(opt.GENERAL).update_one(0, { '$set': { 'raid_start': 1 } })
            time.sleep(0.5)
            channel_list = db(opt.CHANNELS).find({'online': 0, 'raid_events': 1}).distinct('name')
            if channel_list:
                util.queue_message_to_some(messages.raid_event_appear(str(raid_level), str(time_to_join)), channel_list)
            time.sleep(message_interval)
            for i in range(interval_range, 0, -(message_interval)):
                util.queue_message_to_some(messages.raid_event_countdown(str(i)), channel_list)
                time.sleep(message_interval)
            db(opt.GENERAL).update_one(0, { '$set': { 'raid_start': 0 } })
            rand = random.randint(5400, 9000)
            db(opt.GENERAL).update_one(0, { '$set': { 'raid_time': time.time() + rand } })
            if len(raid_users) == 0:
                if channel_list:
                    util.queue_message_to_some(messages.raid_event_no_users, channel_list)
                continue
            elif len(raid_users) == 1:
                user_word = ' user'
            else:
                user_word = ' users'
            for user in raid_users:
                success_rate += math.ceil(db(opt.USERS).find_one_by_id(user[1])['user_level'] / raid_level * 125)
            if channel_list:
                util.queue_message_to_some(messages.raid_event_start(str(len(raid_users)), user_word, str(success_rate/10)), channel_list)
            time.sleep(3)
            raid_success = random.randint(1, 1001)
            if raid_success <= success_rate:
                experience_gain = math.ceil(raid_level**1.2 * 27.5 / len(raid_users))
                if channel_list:
                    util.queue_message_to_some(messages.raid_event_win(str(len(raid_users)), user_word, str(raid_level), str(experience_gain)), channel_list)
                for user, channel in raid_users:
                    users_by_channel[user].append(channel)
                for channel in users_by_channel.items():
                    level_up_users = []
                    for user in channel[1]:
                        db(opt.USERS).update_one(user, {'$inc': {
                            'total_experience': experience_gain,
                            'current_experience': experience_gain,
                            'raid_wins': 1,
                            'raids': 1
                        }})
                        if (((db(opt.USERS).find_one_by_id(user)['user_level']+1)**2)*10) - db(opt.USERS).find_one_by_id(user)['current_experience'] <= 0:
                            while (((db(opt.USERS).find_one_by_id(user)['user_level']+1)**2)*10) - db(opt.USERS).find_one_by_id(user)['current_experience'] <= 0:
                                db(opt.USERS).update_one(user, {'$inc': {
                                    'user_level': 1,
                                    'current_experience': -(((db(opt.USERS).find_one_by_id(user)['user_level']+1)**2)*10)
                                }})
                            level_up_users.append(user)
                    level_up_names = util.get_display_name(0, level_up_users)
                    if level_up_names:
                        i = 1
                        for user in level_up_names[::5]:
                            util.queue_message_to_one(messages.users_level_up(level_up_names[level_up_names.index(user):5*i]), channel[0])
                            i += 1
                db(opt.GENERAL).update_one(0, {'$inc': {
                    'total_experience': experience_gain * len(raid_users),
                    'total_raid_wins': 1
                }})
            else:
                if channel_list:
                    util.queue_message_to_some(messages.raid_event_failed(str(len(raid_users)), user_word, str(raid_level)), channel_list)
                for user in raid_users:
                    db(opt.USERS).update_one(user[0], {'$inc': {
                        'raid_losses': 1,
                        'raids': 1
                    }})
                db(opt.GENERAL).update_one(0, { '$inc': { 'total_raid_losses': 1 } })
            db(opt.GENERAL).update_one(0, { '$inc': { 'total_raids': 1 } })
            raid_users.clear()
            users_by_channel.clear()
        time.sleep(60)

raid_event_thread = threading.Thread(target = raid_event)
raid_event_thread.start()

while True:
    try:
        resp = emoji.demojize(util.sock.recv(4096).decode('utf-8'))
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

            resp_list = resp.splitlines()
            if resp_list:
                for chat_message in resp_list:

                    message = message_regex.search(chat_message)
                    if message:
                        message = message.group(1).strip()
                    else:
                        continue

                    if message.startswith(bot_prefix):
                        params = message[1:].casefold().split(' ')

                        channel = channel_regex.search(chat_message)
                        if channel:
                            channel = channel.group(1)
                        else:
                            continue

                        if db(opt.CHANNELS).find_one({'name': channel})['online'] == 0:

                            user = user_regex.search(chat_message)
                            if user:
                                user = user.group(1)
                            else:
                                continue

                            display_name = name_regex.search(chat_message)
                            if display_name:
                                display_name = display_name.group(1)
                                try:
                                    display_name.encode('ascii')
                                except UnicodeEncodeError:
                                    display_name = err_name_regex.search(chat_message)
                                    if display_name:
                                        display_name = display_name.group(1)
                                    else:
                                        continue
                            else:
                                continue

                            try:
                                user_cmd_use_time = db(opt.USERS).find_one_by_id(user)['cmd_use_time']
                            except:
                                user_cmd_use_time = 0
                            user_cooldown = db(opt.CHANNELS).find_one({'name': channel})['user_cooldown']
                            global_cmd_use_time = db(opt.CHANNELS).find_one({'name': channel})['cmd_use_time']
                            global_cooldown = db(opt.CHANNELS).find_one({'name': channel})['global_cooldown']
                            message_queued = db(opt.CHANNELS).find_one({'name': channel})['message_queued']
                            if time.time() > global_cmd_use_time + global_cooldown and time.time() > user_cmd_use_time + user_cooldown and message_queued == 0:

                                db(opt.USERS).update_one(user, { '$set': { 'username': display_name } }, upsert=True)

                                if params[0] == 'commands' or params[0] == 'help' or params[0] == 'bot':
                                    cmd.commands(channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'enterdungeon' or params[0] == 'ed':
                                    tags = db(opt.TAGS).find_one_by_id(user)
                                    if tags and tags.get('bot') == 1:
                                        continue
                                    else:
                                        cmd.enterdungeon(user, display_name, channel)
                                        db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                        db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'dungeonlvl' or params[0] == 'dungeonlevel':
                                    cmd.dungeonlvl(channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'dungeonmaster' or params[0] == 'dm':
                                    cmd.dungeonmaster(channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'dungeonstats':
                                    cmd.dungeonstats(channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'raidstats':
                                    cmd.raidstats(channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'ping':
                                    cmd.ping(channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'leaderboard' or params[0] == 'lb':
                                    cmd.leaderboard(channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'channels':
                                    cmd.channels(channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'xp' or params[0] == 'exp':
                                    try:
                                        cmd.xp(user, display_name, channel, params[1])
                                    except IndexError:
                                        cmd.xp(user, display_name, channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'lvl' or params[0] == 'level':
                                    try:
                                        cmd.lvl(user, display_name, channel, params[1])
                                    except IndexError:
                                        cmd.lvl(user, display_name, channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                                if params[0] == 'winrate' or params[0] == 'wr':
                                    try:
                                        cmd.winrate(user, display_name, channel, params[1])
                                    except IndexError:
                                        cmd.winrate(user, display_name, channel)
                                    db(opt.CHANNELS).update_one_by_name(channel, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)
                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                            if params[0] == 'register':
                                cmd.register(user, display_name, channel)

                            if params[0] == 'join':
                                tags = db(opt.TAGS).find_one_by_id(user)
                                if tags and tags.get('bot') == 1:
                                    continue
                                else:
                                    dungeon = db(opt.GENERAL).find_one_by_id(0)
                                    channel_raids = db(opt.CHANNELS).find_one({'name': channel})
                                    if dungeon['raid_start'] == 1 and channel_raids['raid_events'] == 1:
                                        if not [usr for usr in raid_users if user in usr]:
                                            raid_user = db(opt.USERS).find_one_by_id(user)
                                            if raid_user and raid_user.get('user_level'):
                                                raid_users.append((channel, raid_user['_id']))
                                            else:
                                                if time.time() > user_cmd_use_time + global_cooldown:
                                                    register_thread = threading.Thread(target = util.queue_message_to_one, args=(messages.not_registered(display_name), channel))
                                                    register_thread.start()
                                                    db(opt.USERS).update_one(user, { '$set': { 'cmd_use_time': time.time() } }, upsert=True)

                            if params[0] == 'suggest':
                                cmd.suggest(display_name, channel, message[len(params[0])+2:])

                        ### Admin Commands ###

                        tags = db(opt.TAGS).find_one_by_id(user)
                        if tags:
                            if params[0] == 'text':
                                if tags.get('admin') == 1:
                                    modes = ['vgr', 'vbr', 'gr', 'br', 'fail']
                                    try:
                                        if params[1] in modes:
                                            util.dungeon_text(params[1], message[len(params[0])+len(params[1])+2:])
                                        else:
                                            util.queue_message_to_one(messages.add_text_error, channel)
                                    except IndexError:
                                        util.queue_message_to_one(messages.add_text_error, channel)

                            if params[0] == 'add':
                                if tags.get('admin') == 1:
                                    try:
                                        util.join_channel(channel, params[1], float(params[2]), float(params[3]))
                                    except IndexError:
                                        if len(params) == 3:
                                            util.join_channel(channel, params[1], float(params[2]), 0)
                                        elif len(params) == 2:
                                            util.join_channel(channel, params[1], 2.5, 0)
                                        else:
                                            util.queue_message_to_one(messages.add_channel_error, channel)
                                    except ValueError as e:
                                        util.queue_message_to_one(messages.error_message(e), channel)

                            if params[0] == 'part':
                                if tags.get('admin') == 1:
                                    try:
                                        util.part_channel(params[1])
                                    except IndexError:
                                        util.queue_message_to_one(messages.part_channel_error, channel)

                                elif tags.get('moderator') == 1:
                                    try:
                                        if params[1] == display_name.casefold():
                                            util.part_channel(params[1])
                                    except IndexError:
                                        util.part_channel(display_name.casefold())

                            if params[0] == 'events':
                                if tags.get('admin') == 1:
                                    try:
                                        util.set_events(params[1], params[2], channel)
                                    except IndexError:
                                        util.queue_message_to_one(messages.set_events_error_admin, channel)

                                elif tags.get('moderator') == 1:
                                    try:
                                        if params[1] == display_name.casefold():
                                            util.set_events(params[1], params[2], channel)
                                        elif params[1] == 'on' or params[1] == 'off':
                                            util.set_events(display_name.casefold(), params[1], channel)
                                    except IndexError:
                                        util.queue_message_to_one(messages.set_events_error_mod, channel)

                            if params[0] == 'cd' or params[0] == 'cooldown':
                                if tags.get('admin') == 1:
                                    try:
                                        util.set_cooldown(params[1], params[2], float(params[3]), channel)
                                    except IndexError:
                                        util.queue_message_to_one(messages.set_cooldown_error, channel)
                                    except ValueError as e:
                                        util.queue_message_to_one(messages.error_message(e), channel)

                            if params[0] == 'eval':
                                if tags.get('admin') == 1:
                                    util.run_eval(message[len(params[0])+2:], channel)

                            if params[0] == 'exec':
                                if tags.get('admin') == 1:
                                    util.run_exec(message[len(params[0])+2:], channel)

                            if params[0] == 'tag':
                                if tags.get('admin') == 1:
                                    try:
                                        util.tag_user(params[1], params[2], channel)
                                    except IndexError as e:
                                        util.queue_message_to_one(messages.tag_error, channel)

                            if params[0] == 'resetcd':
                                if tags.get('admin') == 1:
                                    util.reset_cooldown(channel)

                            if params[0] == 'restart':
                                if tags.get('admin') == 1:
                                    util.restart()
