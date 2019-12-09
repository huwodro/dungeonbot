import emoji

commands = emoji.emojize(':memo:', use_aliases=True) + 'Commands: +register | +enterdungeon | +dungeonlvl | +lvl | +xp | +winrate | +dungeonmaster | +dungeonstats | +dungeonstatus'

pong = 'Dungeon Bot MrDestructoid For a list of commands, type +commands'

def startup_message (branch, sha):
  return emoji.emojize(':arrow_right:', use_aliases=True) + ' Dungeon Bot (' + branch + ', ' + sha[0:7] + ')'

def dungeon_too_low_level(username, dungeonlevel):
  return username + ', the Dungeon [' + dungeonlevel + "] is too low level for you to enter. You won't gain any experience " + emoji.emojize(':crossed_swords:', use_aliases=True)

def dungeon_very_bad_run (username, levelrun, experiencegain):
  return username + ' | Very Bad Run [x0.5] - You beat the dungeon level [' + levelrun + '] - Experience Gained: ' + experiencegain + ' PogChamp'

def dungeon_very_good_run (username, levelrun, experiencegain):
  return username + ' | Very Good Run [x1.5] - You beat the dungeon level [' + levelrun + '] - Experience Gained: ' + experiencegain + ' PogChamp'

def dungeon_bad_run (username, normalrunquality, levelrun, experiencegain):
  return username + ' | Bad Run [x' + normalrunquality + '] - You beat the dungeon level [' + levelrun + '] - Experience Gained: ' + experiencegain + ' PogChamp'

def dungeon_good_run (username, normalrunquality, levelrun, experiencegain):
  return username + ' | Good Run [x' + normalrunquality + '] - You beat the dungeon level [' + levelrun + '] - Experience Gained: ' + experiencegain + ' PogChamp'

def dungeon_failed (username, levelrun):
  return username + ', you failed to beat the dungeon level [' + levelrun + '] - No experience gained FeelsBadMan'

def dungeon_already_entered (username, timeremaining):
  return username + ', you have already entered the dungeon recently, ' + timeremaining + ' left until you can enter again!' + emoji.emojize(' :hourglass:', use_aliases=True)

def dungeon_level (dungeonlevel):
  return emoji.emojize(':shield:', use_aliases=True) + ' Dungeon Level: [' + dungeonlevel + ']'

def dungeon_master (topuser, highestexperience):
  return topuser + ' is the current Dungeon Master with ' + highestexperience + ' experience' + emoji.emojize(' :crown:', use_aliases=True)

def dungeon_masters (numberoftopusers, highestexperience):
  return 'There are ' + numberoftopusers + ' users with ' + highestexperience + ' experience, no one is currently Dungeon Master FeelsBadMan'

dungeon_no_master = 'There is currently no Dungeon Master FeelsBadMan'

def dungeon_general_stats (dungeons, dungeonword, wins, winword, losses, loseword, winrate):
  return 'General Dungeon Stats: ' + dungeons + dungeonword + ' / ' + wins + winword +' / ' + losses + loseword + ' = ' + winrate + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)

def dungeon_uptime (uptime):
  return 'Dungeon Uptime: ' + uptime + emoji.emojize(' :stopwatch:', use_aliases=True)

def dungeon_level_up (dungeonlevel):
  return 'DING PogChamp Dungeon Level [' + dungeonlevel + ']'

def user_level_up (username, userlevel):
  return username + ' just leveled up! Level [' + userlevel + '] PogChamp'

def user_already_registered (username):
  return username + ', you are already a registered user! 4Head'

def user_experience (username, userexperience):
  return username + "'s total experience: " +  userexperience + emoji.emojize(' :diamonds:', use_aliases=True)

def user_no_experience (username):
  return username + ', no experience found for that user!' + emoji.emojize(' :warning:', use_aliases=True)

def user_level (username, userlevel, currentexperience, nextexperience):
  return username + "'s current level: [" + userlevel + '] - XP (' + currentexperience + ' / ' + nextexperience + ')' + emoji.emojize(' :diamonds:', use_aliases=True)

def user_no_level (username):
  return username + ', no level found for that user!' + emoji.emojize (' :warning:')

def you_no_entered_dungeons (username):
  return username + ", you haven't entered any dungeons NotLikeThis"

def user_stats (username, wins, winword, losses, loseword, winrate):
  return username + "'s winrate: " + wins + winword +' / ' + losses + loseword + ' = ' + winrate + '% Winrate' + emoji.emojize(' :diamonds:', use_aliases=True)

def user_no_entered_dungeons (username):
  return username + ", that user hasn't entered any dungeons NotLikeThis"

def you_not_registered (username):
  return username + ', you are not a registered user, type +register to register!' + emoji.emojize(' :game_die:', use_aliases=True)

def user_not_registered (username):
  return username + ', that user is not registered!' + emoji.emojize(' :warning:', use_aliases=True)
