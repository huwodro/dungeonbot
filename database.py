from pymongo import MongoClient
import auth

from bson.json_util import dumps

GENERAL = 'General'
USERS = 'UserStats'
TAGS = 'UserTags'

client = MongoClient(auth.db_host, auth.db_port)
db = client['Twitch']

class MongoDatabase:
  def __init__(self, collection):
    self.collection = collection

  raw = db

  def find_one(self, f=None, *args, **options):
    return db[self.collection].find_one(f, *args, **options)

  def update_one(self, f, update, **options):
    return db[self.collection].update_one({ '_id': f }, update, **options)

  # def update_many(self, f, update, **options):
  #   return db[self.collection].update_many( f, update, **options )

  def count_documents(self, f, **options):
    return db[self.collection].count_documents(f, **options)

  def find_one_by_id(self, i, **options):
    options.update(limit=1)
    return self.find_one({ '_id': i }, **options)
