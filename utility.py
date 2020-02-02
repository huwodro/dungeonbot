import os
import random
import re
import socket
import sys
import threading
import time

import datetime

import requests
import emoji
import git

import auth
import database as opt
import schemes
import messages

db = opt.MongoDatabase

server = 'irc.chat.twitch.tv'
port = 6667

def connect(manual = False):
    global sock
    sock = socket.socket()
    try:
        sock.connect((server, port))
        sock.send(('PASS ' + auth.token + '\r\n').encode('utf-8'))
        sock.send(('NICK ' + auth.nickname + '\r\n').encode('utf-8'))
        sock.send(("CAP REQ :twitch.tv/tags\r\n").encode('utf-8'))
        channels = ''
        for channel in db.raw[opt.CHANNELS].find():
            channels += '#' + channel['name'] + ','
        sock.send(('JOIN ' + channels + '\r\n').encode('utf-8'))
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        sys.stdout.write(current_time + ': SOCKET CONNECTED\n')
        sys.stdout.flush()
    except socket.error as e:
        sys.stderr.write('SOCKET ERROR: ' + str(e.errno) + '\n')
        sys.stderr.flush()
        if not manual:
            time.sleep(auth.reconnect_timer)
        else:
            os._exit(1) # Shuts down script if called from initialization

def get_display_name(id, list = None):
    headers = { 'Authorization': auth.bearer }
    if list:
        params = (('id', list),)
    else:
        params = (('id', id),)
    response = requests.get('https://api.twitch.tv/helix/users', headers=headers, params=params).json()
    if list:
        try:
            name_list = []
            for user in response['data']:
                name_list.append(user['display_name'])
            return name_list
        except:
            return
    else:
        try:
            return response['data'][0]['display_name']
        except:
            return

def get_login_name(id):
    headers = { 'Authorization': auth.bearer }
    params = (('id', id),)
    response = requests.get('https://api.twitch.tv/helix/users', headers=headers, params=params).json()
    try:
        return response['data'][0]['login']
    except:
        return

def get_user_id(user):
    headers = { 'Authorization': auth.bearer }
    params = (('login', user),)
    response = requests.get('https://api.twitch.tv/helix/users', headers=headers, params=params).json()
    try:
        return response['data'][0]['id']
    except:
        return

def pong():
    sock.send(('PONG :tmi.twitch.tv\r\n').encode('utf-8'))

last_time_symbol = 0
def get_cooldown_bypass_symbol():
    global last_time_symbol
    if last_time_symbol == 0:
        last_time_symbol = 1
        return ''
    else:
        last_time_symbol = 0
        return ' \U000e0000'

def send_message(message, channel):
    msg = 'PRIVMSG #' + channel + ' :' + message + get_cooldown_bypass_symbol()
    sock.send((msg + '\r\n').encode('utf-8'))

queue_message_lock = threading.Lock()

def queue_message(message, mode, channel = None):
    queue_message_lock.acquire()
    if channel == None:
        for channel in db.raw[opt.CHANNELS].find():
            if db(opt.CHANNELS).find_one_by_id(channel['_id'])['online'] == 0:
                db(opt.CHANNELS).update_one(channel['_id'], { '$set': { 'message_queued': 1 } } )
    else:
        channel_id = get_user_id(channel)
        db(opt.CHANNELS).update_one(channel_id, { '$set': { 'message_queued': 1 } } )
    time.sleep(1.25)
    if mode == 0:
        msg = 'PRIVMSG #' + channel + ' :' + message + get_cooldown_bypass_symbol()
        sock.send((msg + '\r\n').encode('utf-8'))
        db(opt.CHANNELS).update_one(channel_id, { '$set': { 'message_queued': 0 } } )
    else:
        msg = ''
        for channel in db.raw[opt.CHANNELS].find():
            if db(opt.CHANNELS).find_one_by_id(channel['_id'])['online'] == 0:
                msg += 'PRIVMSG #' + channel['name'] + ' :' + message + get_cooldown_bypass_symbol() + '\r\n'
                db(opt.CHANNELS).update_one(channel['_id'], { '$set': { 'message_queued': 0 } } )
        sock.send((msg).encode('utf-8'))
    queue_message_lock.release()

def whisper(user, message, channel):
    msg = 'PRIVMSG #' + channel + ' :.w ' + user + ' ' + message
    sock.send((msg + '\r\n').encode('utf-8'))

def git_info():
    repo = git.Repo(search_parent_directories=True)
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    queue_message(messages.startup_message(branch, sha), 1)

def start():
    default_admin_id = get_user_id(auth.default_admin)
    default_admin = db(opt.TAGS).find_one_by_id(default_admin_id)
    if default_admin == None:
        db(opt.TAGS).update_one(default_admin_id, {'$set': { 'admin': 1 } }, upsert=True)
    default_channel_id = get_user_id(auth.default_channel)
    default_channel = db(opt.CHANNELS).find_one_by_id(default_channel_id)
    if default_channel == None:
        db(opt.CHANNELS).update_one(default_channel_id, { '$set': schemes.CHANNELS }, upsert=True)
        db(opt.CHANNELS).update_one(default_channel_id, { '$set': { 'name': auth.default_channel } }, upsert=True)
    connect(True) # True for initialization
    default_dungeon = db(opt.GENERAL).find_one_by_id(0)
    if default_dungeon == None:
        db(opt.GENERAL).update_one(0, { '$set': schemes.GENERAL }, upsert=True)
    git_info()

def check_if_registered(user_id, channel, req=None):
    same_user = req == user_id if req else True
    if same_user:
        user = db(opt.USERS).find_one_by_id(user_id)
        if user and user.get('user_level'):
            return True
        else:
            send_message(messages.not_registered(get_display_name(user_id)), channel)
    else:
        target = db(opt.USERS).find_one_by_id(req)
        if target and target.get('user_level'):
            return True
        else:
            send_message(messages.user_not_registered(get_display_name(user_id)), channel)
    return False

def suggest(user, channel, message):
    if message != '':
        suggestions = db(opt.SUGGESTIONS).count_documents({})
        if suggestions < 500:
            try:
                id = db(opt.SUGGESTIONS).find_one(sort=[('_id', -1)])['_id']
            except:
                id = 0
            else:
                id += 1
            db(opt.SUGGESTIONS).update_one(id, {'$set': {
                'user': user,
                'suggestion': message
            }}, upsert=True)
            suggestion_thread = threading.Thread(target = queue_message, args=(messages.suggestion_message(user, str(id)), 0, channel))
            suggestion_thread.start()

### Admin Commands ###

def dungeon_text(mode, message):
    texts = db(opt.TEXT).count_documents({})
    try:
        id = db(opt.TEXT).find_one(sort=[('_id', -1)])['_id']
    except:
        id = 0
    else:
        id += 1
    db(opt.TEXT).update_one(id, {'$set': {
        'mode': mode,
        'text': message
    }}, upsert=True)

def check_suggestion(user, channel, id):
    suggestion = db(opt.SUGGESTIONS).find_one_by_id(id)['suggestion']
    suggestion_user = db(opt.SUGGESTIONS).find_one_by_id(id)['user']
    whisper(get_display_name(user), messages.check_suggestion(suggestion, suggestion_user, str(id)), channel)

def remove_suggestion(user, channel, id):
    suggestion = db(opt.SUGGESTIONS).find_one_by_id(id)
    if suggestion:
        db(opt.SUGGESTIONS).delete_one(id)
        whisper(get_display_name(user), messages.suggestion_removed(str(id)), channel)
    else:
        whisper(get_display_name(user), messages.remove_suggestion_error, channel)

def join_channel(current_channel, channel, global_cooldown, user_cooldown):
    try:
        user = get_user_id(channel)
        if user:
            db(opt.CHANNELS).update_one(user, {'$set': {
                'name': channel,
                'online': 1,
                'cmdusetime': time.time(),
                'global_cooldown': global_cooldown,
                'user_cooldown': user_cooldown,
                'message_queued': 0
            }}, upsert=True)
            db(opt.TAGS).update_one(user, {'$set': { 'moderator': 1 } }, upsert=True)
            sock.send(('JOIN #' + channel + '\r\n').encode('utf-8'))
            repo = git.Repo(search_parent_directories=True)
            branch = repo.active_branch.name
            sha = repo.head.object.hexsha
            send_message(messages.startup_message(branch, sha), channel)
    except AttributeError:
        queue_message(messages.no_channel_error(channel), 0, current_channel)

def part_channel(channel):
    user = db(opt.CHANNELS).find_one({'name': channel})
    if user:
        part_channel_thread = threading.Thread(target = queue_message, args=(messages.leaving_channel(get_display_name(user['_id'])), 0, channel))
        part_channel_thread.start()
        db(opt.CHANNELS).delete_one(user['_id'])
        db(opt.TAGS).update_one(user['_id'], {'$unset': { 'moderator': '' } }, upsert=True)
        sock.send(('PART #' + channel + '\r\n').encode('utf-8'))

def list_channels(channel):
    joined_channels = []
    for joined_channel in db.raw[opt.CHANNELS].find():
        joined_channels.append(joined_channel['name'])
    queue_message(messages.list_channels(joined_channels), 0, channel)

def set_cooldown(channel, mode, cooldown, current_channel):
    channel_id = get_user_id(channel)
    if db(opt.CHANNELS).find_one_by_id(channel_id):
        if mode == 'global':
            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'global_cooldown': cooldown } } )
        elif mode == 'user':
            db(opt.CHANNELS).update_one(channel_id, { '$set': { 'user_cooldown': cooldown } } )
        else:
            queue_message(messages.set_cooldown_error, 0, current_channel)

def run_eval(channel, expression):
    try:
        queue_message(str(eval(expression)), 0, channel)
    except Exception as e:
        queue_message(messages.error_message(e), 0, channel)

def run_exec(channel, code):
    try:
        exec(code)
    except Exception as e:
        queue_message(messages.error_message(e), 0, channel)

def reset_cooldown(channel):
    for user in db.raw[opt.USERS].find():
        db(opt.USERS).update_one(user['_id'], { '$set': {
            'last_entry': 0,
            'next_entry': 0
        }})
    queue_message(messages.reset_cooldown, 1)

def restart():
    queue_message(messages.restart_message, 1)
    repo = git.Repo(search_parent_directories=True)
    repo.git.reset('--hard')
    repo.remotes.origin.pull()
    sock.send(('QUIT\r\n').encode('utf-8'))
    sock.close()
    os._exit(1)

def tag_user(channel, user, tag):
    tag_list = ['admin', 'moderator']
    user_id = get_user_id(user)
    if user:
        if tag.lower() in tag_list:
            user = db(opt.TAGS).find_one_by_id(user_id)
            if not user or not user.get(tag.lower()):
                db(opt.TAGS).update_one(user_id, {'$set': {tag.lower(): 1} }, upsert=True)
                queue_message(messages.tag_message(get_display_name(user_id), tag), 0, channel)
            else:
                queue_message(messages.already_tag_message(get_display_name(user_id), tag), 0, channel)
