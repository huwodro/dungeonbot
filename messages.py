import random

import emoji

import database as opt

db = opt.MongoDatabase

commands = emoji.emojize(':memo:', use_aliases=True) + 'Commands: +register | +enterdungeon | +dungeonlvl | +lvl | +xp | +winrate | +dungeonmaster | +dungeonstats | +raidstats | +uptime | +suggest'

bot_description = 'Dungeon Bot MrDestructoid Made by Huwodro. For a list of commands, type +commands'

pong = 'Dungeon Bot MrDestructoid For a list of commands, type +commands'

def startup_message(branch, sha):
    return emoji.emojize(':arrow_right:', use_aliases=True) + ' Dungeon Bot (' + branch + ', ' + sha[0:7] + ')'

def dungeon_too_low_level(username, dungeonlevel):
    return username + ', the Dungeon [' + dungeonlevel + "] is too low level for you to enter. You won't gain any experience!" + emoji.emojize(':crossed_swords:', use_aliases=True)

def dungeon_very_bad_run(username, experiencegain):
    try:
        message = emoji.emojize(list(db(opt.TEXT).get_random_documents_by_match({'mode': 'vbr'}, 1))[0]['text'])
    except:
        message = 'Very Bad Run'
    return username + ' | ' + message + ' | Experience Gained: ' + experiencegain + emoji.emojize(':gem:', use_aliases=True)

def dungeon_very_good_run(username, experiencegain):
    try:
        message = emoji.emojize(list(db(opt.TEXT).get_random_documents_by_match({'mode': 'vgr'}, 1))[0]['text'])
    except:
        message = 'Very Good Run'
    return username + ' | ' + message + ' | Experience Gained: ' + experiencegain + emoji.emojize(':gem:', use_aliases=True)

def dungeon_bad_run(username, experiencegain):
    try:
        message = emoji.emojize(list(db(opt.TEXT).get_random_documents_by_match({'mode': 'br'}, 1))[0]['text'])
    except:
        message = 'Bad Run'
    return username + ' | ' + message + ' | Experience Gained: ' + experiencegain + emoji.emojize(':gem:', use_aliases=True)

def dungeon_good_run(username, experiencegain):
    try:
        message = emoji.emojize(list(db(opt.TEXT).get_random_documents_by_match({'mode': 'gr'}, 1))[0]['text'])
    except:
        message = 'Good Run'
    return username + ' | ' + message + ' | Experience Gained: ' + experiencegain + emoji.emojize(':gem:', use_aliases=True)

def dungeon_failed(username):
    try:
        message = emoji.emojize(list(db(opt.TEXT).get_random_documents_by_match({'mode': 'fail'}, 1))[0]['text'])
    except:
        message = 'Failed Run'
    return username + ' | ' + message + ' | No experience gained! FeelsBadMan'

def dungeon_already_entered(username, timeremaining):
    return username + ', you have already entered the dungeon recently, ' + timeremaining + ' left until you can enter again!' + emoji.emojize(' :hourglass:', use_aliases=True)

def dungeon_level(dungeonlevel):
    return emoji.emojize(':shield:', use_aliases=True) + ' Dungeon Level: [' + dungeonlevel + ']'

def dungeon_master(topuser, highestexperience, userlevel):
    return topuser + ' is the current Dungeon Master at Level [' + userlevel + '] with ' + highestexperience + ' experience!' + emoji.emojize(' :crown:', use_aliases=True)

def dungeon_masters(numberoftopusers, highestexperience, userlevel):
    return 'There are ' + numberoftopusers + ' users at Level [' + userlevel + '] with ' + highestexperience + ' experience, no one is currently Dungeon Master! FeelsBadMan'

dungeon_no_master = 'There is currently no Dungeon Master! FeelsBadMan'

def dungeon_general_stats(dungeons, dungeonword, wins, winword, losses, loseword, winrate):
    return 'General Dungeon Stats: ' + dungeons + dungeonword + ' / ' + wins + winword +' / ' + losses + loseword + ' = ' + winrate + '% Winrate' + emoji.emojize(' :large_blue_diamond:', use_aliases=True)

def raid_general_stats(raids, raidword, wins, winword, losses, loseword, winrate):
    return 'General Raid Stats: ' + raids + raidword + ' / ' + wins + winword +' / ' + losses + loseword + ' = ' + winrate + '% Winrate' + emoji.emojize(' :large_orange_diamond:', use_aliases=True)

def raid_event_appear(raidlevel, time):
    return 'A Raid Event at Level [' + raidlevel + '] has appeared. Type +join to join the raid! The raid will begin in ' + time + ' seconds!' + emoji.emojize(':zap:', use_aliases=True)

def raid_event_countdown(time):
    return 'The raid will begin in ' + time + ' seconds. Type +join to join the raid!' + emoji.emojize(':zap:', use_aliases=True)

def raid_event_no_users():
    return '0 users joined the raid!' + emoji.emojize(':skull_and_crossbones:', use_aliases=True)

def raid_event_start(users, userword, successrate):
    return 'The raid has begun with ' + users + userword + '! [' + successrate + '%]' + emoji.emojize(':crossed_swords:', use_aliases=True)

def raid_event_win(users, userword, raidlevel, experiencegain):
    return users + userword + ' beat the raid level [' + raidlevel + '] - ' + experiencegain + ' experience rewarded!' + emoji.emojize(':gem:', use_aliases=True)

def raid_event_failed(users, userword, raidlevel):
    return users + userword + ' failed to beat the raid level [' + raidlevel + '] - No experience rewarded!' + emoji.emojize(':skull:', use_aliases=True)

def dungeon_uptime(uptime):
    return 'Dungeon Uptime: ' + uptime + emoji.emojize(' :stopwatch:', use_aliases=True)

def dungeon_level_up(dungeonlevel):
    return 'DING PogChamp Dungeon Level [' + dungeonlevel + ']'

def user_level_up(username, userlevel):
    return username + ' just leveled up! Level [' + userlevel + '] PogChamp'

def users_level_up(users):
    return ', '.join(users) + ' just leveled up! PogChamp'

def user_already_registered(username):
    return username + ', you are already a registered user! 4Head'

def user_experience(username, userexperience):
    return username + "'s total experience: " +  userexperience + emoji.emojize(' :diamonds:', use_aliases=True)

def user_no_experience(username):
    return username + ', no experience found for that user!' + emoji.emojize(' :warning:', use_aliases=True)

def user_level(username, userlevel, currentexperience, nextexperience):
    return username + "'s current level: [" + userlevel + '] - XP (' + currentexperience + ' / ' + nextexperience + ')' + emoji.emojize(' :diamonds:', use_aliases=True)

def user_no_level(username):
    return username + ', no level found for that user!' + emoji.emojize (' :warning:')

def you_no_entered_dungeons (username):
    return username + ", you haven't entered any dungeons! NotLikeThis"

def user_stats(username, wins, winword, losses, loseword, winrate):
    return username + "'s winrate: " + wins + winword +' / ' + losses + loseword + ' = ' + winrate + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)

def user_no_entered_dungeons(username):
    return username + ", that user hasn't entered any dungeons! NotLikeThis"

def you_not_registered(username):
    return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)

def user_not_registered(username):
    return username + ', that user is not registered!' + emoji.emojize(' :warning:', use_aliases=True)

def suggestion_message(username, id):
    return username + ', thanks for your suggestion! ' + emoji.emojize(':memo:', use_aliases=True) + ' [ID ' + id + ']'

def check_suggestion(suggestion, user, id):
    return '\"' + suggestion + '\"' + ' - ' + user + ' [ID ' + id + ']'

def suggestion_removed(id):
    return 'Suggestion [ID ' + id + '] removed!'

remove_suggestion_usage_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +rs <id>'

remove_suggestion_error = emoji.emojize(':warning: ', use_aliases=True) + 'No such ID!'

no_suggestions = 'There are no suggestions!' + emoji.emojize(':memo:', use_aliases=True)

def no_channel_error(channel):
    return emoji.emojize(':x: ', use_aliases=True) + 'channel ' + channel + ' does not exist'

def leaving_channel(name):
    return emoji.emojize(':rewind:', use_aliases=True) + ' Leaving ' + name + ' FeelsBadMan'

def list_channels(list):
    return '[' + ', '.join(list) + ']'

def list_suggestions(list):
    return '[' + ', '.join(str(i) for i in list) + ']'

reset_cooldown = 'Cooldowns reset for all users' + emoji.emojize(' :stopwatch:', use_aliases=True)

def tag_message(user, tag):
    return user + ' set to ' + tag.capitalize() + emoji.emojize(' :bell:', use_aliases=True)

def error_message(error):
    return emoji.emojize(':x: ', use_aliases=True) + str(error)

add_text_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +text <vgr/vbr/gr/br/fail> <message>)'

add_channel_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +add <name> (optional: <global cooldown> <user cooldown>)'

part_channel_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +part <name>'

set_cooldown_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +cd <channel> <global/user> <cooldown>'

tag_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +tag <user> <role>'

restart_message = emoji.emojize(':arrows_counterclockwise:', use_aliases=True) + ' Restarting...'
