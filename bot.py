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

util.start()

def live_check():
    while True:
        online_channels = []
        headers = { 'Authorization': auth.bearer }
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
                online_channels.append(online['user_id'])
            for channel in db.raw[opt.CHANNELS].find():
                if channel['_id'] in online_channels:
                    db(opt.CHANNELS).update_one(channel['_id'], { '$set': { 'online': 1 } }, upsert=True)
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
            util.queue_message(messages.raid_event_appear(str(raid_level), str(time_to_join)), 1)
            time.sleep(message_interval)
            for i in range(interval_range, 0, -(message_interval)):
                util.queue_message(messages.raid_event_countdown(str(i)), 1)
                time.sleep(message_interval)
            db(opt.GENERAL).update_one(0, { '$set': { 'raid_start': 0 } })
            rand = random.randint(3600, 7200)
            db(opt.GENERAL).update_one(0, { '$set': { 'raid_time': time.time() + rand } })
            if len(raid_users) == 0:
                util.queue_message(messages.raid_event_no_users, 1)
                continue
            elif len(raid_users) == 1:
                user_word = ' user'
            else:
                user_word = ' users'
            for user in raid_users:
                success_rate += math.ceil(db(opt.USERS).find_one_by_id(user[1])['user_level'] / raid_level * 125)
            util.queue_message(messages.raid_event_start(str(len(raid_users)), user_word, str(success_rate/10)), 1)
            time.sleep(3)
            raid_success = random.randint(1, 1001)
            if raid_success <= success_rate:
                experience_gain = int(raid_level**1.2 * 275 / len(raid_users))
                util.queue_message(messages.raid_event_win(str(len(raid_users)), user_word, str(raid_level), str(experience_gain)), 1)
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
                        if (((db(opt.USERS).find_one_by_id(user)['user_level']+1)**2)*100) - db(opt.USERS).find_one_by_id(user)['current_experience'] <= 0:
                            while (((db(opt.USERS).find_one_by_id(user)['user_level']+1)**2)*100) - db(opt.USERS).find_one_by_id(user)['current_experience'] <= 0:
                                db(opt.USERS).update_one(user, {'$inc': {
                                    'user_level': 1,
                                    'current_experience': -(((db(opt.USERS).find_one_by_id(user)['user_level']+1)**2)*100)
                                }})
                            level_up_users.append(user)
                    level_up_names = util.get_display_name(0, level_up_users)
                    if level_up_names:
                        i = 1
                        for user in level_up_names[::5]:
                            util.queue_message(messages.users_level_up(level_up_names[level_up_names.index(user):5*i]), 0, channel[0])
                            i += 1
                db(opt.GENERAL).update_one(0, {'$inc': {
                    'total_experience': experience_gain * len(raid_users),
                    'total_raid_wins': 1
                }})
            else:
                util.queue_message(messages.raid_event_failed(str(len(raid_users)), user_word, str(raid_level)), 1)
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
            user = re.search('user-id=(.+?);', resp)
            if user:
                user = user.group(1)
            else:
                continue
            channel = re.search('( PRIVMSG #(.+?) )', resp)
            if channel:
                channel = channel.group(2)
            else:
                continue
            message = re.search('.*#[^:]*:(.*)', resp)
            if message:
                message = message.group(1).strip()
            else:
                continue

            if message.startswith(bot_prefix):
                params = message[1:].casefold().split(' ')

                if db(opt.CHANNELS).find_one_by_id(util.get_user_id(channel))['online'] == 0:
                    channel_id = util.get_user_id(channel)
                    try:
                        user_cmdusetime = db(opt.USERS).find_one_by_id(user)['cmdusetime']
                    except:
                        user_cmdusetime = 0
                    user_cooldown = db(opt.CHANNELS).find_one_by_id(channel_id)['user_cooldown']
                    global_cmdusetime = db(opt.CHANNELS).find_one_by_id(channel_id)['cmdusetime']
                    global_cooldown = db(opt.CHANNELS).find_one_by_id(channel_id)['global_cooldown']
                    message_queued = db(opt.CHANNELS).find_one_by_id(channel_id)['message_queued']
                    if time.time() > global_cmdusetime + global_cooldown and time.time() > user_cmdusetime + user_cooldown and message_queued == 0:

                        if params[0] == 'commands' or params[0] == 'help' or params[0] == 'bot':
                            cmd.commands(channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'enterdungeon' or params[0] == 'ed':
                            cmd.enter_dungeon(user, channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'dungeonlvl' or params[0] == 'dungeonlevel':
                            cmd.dungeon_level(channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'dungeonmaster' or params[0] == 'dm':
                            cmd.dungeon_master(channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'dungeonstats':
                            cmd.dungeon_stats(channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'raidstats':
                            cmd.raid_stats(channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'uptime':
                            cmd.bot_uptime(channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'ping':
                            cmd.ping(channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'xp' or params[0] == 'exp':
                            try:
                                cmd.user_experience(user, channel, params[1])
                            except IndexError:
                                cmd.user_experience(user, channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'lvl' or params[0] == 'level':
                            try:
                                cmd.user_level(user, channel, params[1])
                            except IndexError:
                                cmd.user_level(user, channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                        if params[0] == 'winrate' or params[0] == 'wr':
                            try:
                                cmd.winrate(user, channel, params[1])
                            except IndexError:
                                cmd.winrate(user, channel)
                            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'cmdusetime': time.time() } }, upsert=True)
                            db(opt.USERS).update_one(user, { '$set': { 'cmdusetime': time.time() } }, upsert=True)

                    if params[0] == 'register':
                        cmd.register(user, channel, channel_id)

                    if params[0] == 'join':
                        dungeon = db(opt.GENERAL).find_one_by_id(0)
                        if dungeon['raid_start'] == 1:
                            if not [usr for usr in raid_users if user in usr]:
                                user = db(opt.USERS).find_one_by_id(user)
                                if user and user.get('user_level'):
                                    raid_users.append((channel, user['_id']))
                                else:
                                    register_thread = threading.Thread(target = util.queuemessage, args=(messages.you_not_registered(user), 0, channel))
                                    register_thread.start()

                if params[0] == 'suggest':
                    util.suggest(util.get_display_name(user), channel, message[len(params[0])+2:])

                ### Admin Commands ###

                if params[0] == 'text':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        modes = ['vgr', 'vbr', 'gr', 'br', 'fail']
                        try:
                            if params[1] in modes:
                                util.dungeon_text(params[1], message[len(params[0])+len(params[1])+2:])
                            else:
                                util.queue_message(messages.add_text_error, 0, channel)
                        except IndexError:
                            util.queue_message(messages.add_text_error, 0, channel)

                if params[0] == 'cs':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        try:
                            util.check_suggestion(user, channel, int(params[1]))
                        except:
                            suggestions = []
                            for suggestion in db.raw[opt.SUGGESTIONS].find():
                                suggestions.append(suggestion['_id'])
                            if suggestions:
                                util.whisper(util.get_display_name(user), messages.list_suggestions(suggestions), channel)
                            else:
                                util.whisper(util.get_display_name(user), messages.no_suggestions, channel)

                if params[0] == 'rs':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        try:
                            util.remove_suggestion(user, channel, int(params[1]))
                        except IndexError:
                            util.whisper(user, messages.remove_suggestion_usage_error, channel)
                        except ValueError as e:
                            util.whisper(user, messages.error_message(e), channel)

                if params[0] == 'add':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        try:
                            util.join_channel(channel, params[1], float(params[2]), float(params[3]))
                        except IndexError:
                            if len(params) == 3:
                                util.join_channel(channel, params[1], float(params[2]), 0)
                            elif len(params) == 2:
                                util.join_channel(channel, params[1], 2.5, 0)
                            else:
                                util.queue_message(messages.add_channel_error, 0, channel)
                        except ValueError as e:
                            util.queue_message(messages.error_message(e), 0, channel)

                if params[0] == 'part':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin:
                        if admin.get('moderator') == 1:
                            try:
                                if params[1] == util.get_login_name(user):
                                    util.part_channel(params[1])
                            except IndexError:
                                util.part_channel(util.get_login_name(user))
                        if admin.get('admin') == 1:
                            try:
                                util.part_channel(params[1])
                            except IndexError:
                                util.queue_message(messages.part_channel_error, 0, channel)

                if params[0] == 'cd' or params[0] == 'cooldown':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        try:
                            util.set_cooldown(params[1], params[2], float(params[3]), channel)
                        except IndexError:
                            util.queue_message(messages.set_cooldown_error, 0, channel)
                        except ValueError as e:
                            util.queue_message(messages.error_message(e), 0, channel)

                if params[0] == 'channels':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        util.list_channels(channel)

                if params[0] == 'eval':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        util.run_eval(channel, message[len(params[0])+2:])

                if params[0] == 'exec':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        util.run_exec(channel, message[len(params[0])+2:])

                if params[0] == 'tag':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        try:
                            util.tag_user(channel, params[1], params[2])
                        except IndexError as e:
                            util.queue_message(messages.tag_error, 0, channel)

                if params[0] == 'resetcd':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        util.reset_cooldown(channel)

                if params[0] == 'restart':
                    admin = db(opt.TAGS).find_one_by_id(user)
                    if admin and admin.get('admin') == 1:
                        util.restart()
