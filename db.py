from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['Twitch']
generalcollection = db['General']
usercollection = db['UserStats']
tagcollection = db['UserTags']
