import random
import time

rand = random.randint(3600, 7200)

DUNGEON = {
  'open': 0,
  'dungeon_level': 0,
  'total_experience': 0,
  'total_dungeons': 0,
  'total_wins': 0,
  'total_losses': 0,
  'raid_time': time.time() + rand,
  'total_raids': 0,
  'total_raid_wins': 0,
  'total_raid_losses': 0
}

USER = {
  'user_level': 1,
  'total_experience': 0,
  'current_experience': 0,
  'dungeons': 0,
  'dungeon_wins': 0,
  'dungeon_losses': 0,
  'entered': 0,
  'last_entry': 0,
  'next_entry': 0
}
