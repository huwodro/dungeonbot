import emoji

def commands(command_list):
    return emoji.emojize(':memo:', use_aliases=True) + 'Commands: ' + ' | '.join('+{0}'.format(c) for c in command_list)

def ping(uptime):
    return emoji.emojize(' :stopwatch:', use_aliases=True) + ' Dungeon Bot Uptime: ' + uptime + ' | For a list of commands, type +commands'

def startup_message(branch, sha):
    return emoji.emojize(':arrow_right:', use_aliases=True) + ' Dungeon Bot (' + branch + ', ' + sha[0:7] + ')'

def dungeon_too_low_level(username, dungeon_level):
    return username + ', the Dungeon [' + dungeon_level + "] is too low level for you to enter. You won't gain any experience!" + emoji.emojize(':crossed_swords:', use_aliases=True)

def dungeon_very_bad_run(username, message, experience_gain):
    return username + ' | ' + message + ' | Experience Gained: ' + experience_gain + emoji.emojize(':gem:', use_aliases=True)

def dungeon_very_good_run(username, message, experience_gain):
    return username + ' | ' + message + ' | Experience Gained: ' + experience_gain + emoji.emojize(':gem:', use_aliases=True)

def dungeon_bad_run(username, message, experience_gain):
    return username + ' | ' + message + ' | Experience Gained: ' + experience_gain + emoji.emojize(':gem:', use_aliases=True)

def dungeon_good_run(username, message, experience_gain):
    return username + ' | ' + message + ' | Experience Gained: ' + experience_gain + emoji.emojize(':gem:', use_aliases=True)

def dungeon_failed(username, message):
    return username + ' | ' + message + ' | No experience gained! FeelsBadMan'

def dungeon_already_entered(username, time_remaining):
    return username + ', you have already entered the dungeon recently, ' + time_remaining + ' left until you can enter again!' + emoji.emojize(' :hourglass:', use_aliases=True)

def dungeon_level(dungeon_level):
    return emoji.emojize(':shield:', use_aliases=True) + ' Dungeon Level: [' + dungeon_level + ']'

def dungeon_master(top_user, user_level, highest_experience):
    return top_user + ' is the current Dungeon Master at Level [' + user_level + '] with ' + highest_experience + ' experience!' + emoji.emojize(' :crown:', use_aliases=True)

def dungeon_masters(number_of_top_users, user_level, highest_experience):
    return 'There are ' + number_of_top_users + ' users at Level [' + user_level + '] with ' + highest_experience + ' experience, no one is currently Dungeon Master! FeelsBadMan'

dungeon_no_master = 'There is currently no Dungeon Master! FeelsBadMan'

def dungeon_general_stats(dungeons, dungeon_word, wins, win_word, losses, lose_word, winrate):
    return 'General Dungeon Stats: ' + dungeons + dungeon_word + ' / ' + wins + win_word +' / ' + losses + lose_word + ' = ' + winrate + '% Winrate' + emoji.emojize(' :large_blue_diamond:', use_aliases=True)

def raid_general_stats(raids, raid_word, wins, win_word, losses, lose_word, winrate):
    return 'General Raid Stats: ' + raids + raid_word + ' / ' + wins + win_word +' / ' + losses + lose_word + ' = ' + winrate + '% Winrate' + emoji.emojize(' :large_orange_diamond:', use_aliases=True)

def raid_event_appear(raid_level, time):
    return 'A Raid Event at Level [' + raid_level + '] has appeared. Type +join to join the raid! The raid will begin in ' + time + ' seconds!' + emoji.emojize(':zap:', use_aliases=True)

def raid_event_countdown(time):
    return 'The raid will begin in ' + time + ' seconds. Type +join to join the raid!' + emoji.emojize(':zap:', use_aliases=True)

raid_event_no_users = '0 users joined the raid!' + emoji.emojize(':skull_and_crossbones:', use_aliases=True)

def raid_event_start(users, user_word, success_rate):
    return 'The raid has begun with ' + users + user_word + '! [' + success_rate + '%]' + emoji.emojize(':crossed_swords:', use_aliases=True)

def raid_event_win(users, user_word, raid_level, experience_gain):
    return users + user_word + ' beat the raid level [' + raid_level + '] - ' + experience_gain + ' experience rewarded!' + emoji.emojize(':gem:', use_aliases=True)

def raid_event_failed(users, user_word, raid_level):
    return users + user_word + ' failed to beat the raid level [' + raid_level + '] - No experience rewarded!' + emoji.emojize(':skull:', use_aliases=True)

def user_register(username, dungeon_level):
    return 'DING ' + emoji.emojize(':bell:', use_aliases=True) + ' Thank you for registering ' + username + ' | Dungeon leveled up! Level [' + dungeon_level + ']'

def user_level_up(username, user_level):
    return username + ' just leveled up! Level [' + user_level + '] PogChamp'

def users_level_up(users):
    return ', '.join(users) + ' just leveled up! PogChamp'

def user_register(username, dungeon_level):
    return 'DING ' + emoji.emojize(':bell:', use_aliases=True) + ' Thank you for registering ' + username + ' | Dungeon leveled up! Level [' + dungeon_level + ']'

def user_already_registered(username):
    return username + ', you are already registered! ' + emoji.emojize(':warning:', use_aliases=True)

def user_experience(username, user_experience):
    return username + "'s total experience: " +  user_experience + emoji.emojize(' :diamonds:', use_aliases=True)

def user_level(username, user_level, current_experience, next_experience):
    return username + "'s current level: [" + user_level + '] - XP (' + current_experience + ' / ' + next_experience + ')' + emoji.emojize(' :diamonds:', use_aliases=True)

def no_entered_dungeons (username):
    return username + ", you haven't entered any dungeons!" + emoji.emojize(' :warning:')

def user_stats(username, wins, win_word, losses, lose_word, winrate):
    return username + "'s winrate: " + wins + win_word +' / ' + losses + lose_word + ' = ' + winrate + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)

def user_no_entered_dungeons(username):
    return username + ", that user hasn't entered any dungeons!" + emoji.emojize(' :warning:')

def not_registered(username):
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

def already_tag_message(user, tag):
    return user + ' is already ' + tag.capitalize() + emoji.emojize(' :bell:', use_aliases=True)

def error_message(error):
    return emoji.emojize(':x: ', use_aliases=True) + str(error)

add_text_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +text <vgr/vbr/gr/br/fail> <message>)'

add_channel_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +add <name> (optional: <global cooldown> <user cooldown>)'

part_channel_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +part <name>'

set_events_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +events <channel> <on/off>'

set_cooldown_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +cd <channel> <global/user> <cooldown>'

tag_error = emoji.emojize(':warning: ', use_aliases=True) + 'Insufficient parameters - usage: +tag <user> <role>'

restart_message = emoji.emojize(':arrows_counterclockwise:', use_aliases=True) + ' Restarting...'
