from pymongo import MongoClient
from pymongo.database import Database, Collection
from src.utils.constants import MONGO_DBNAME, MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USERNAME
from bson.objectid import ObjectId


class Mongo(object):
    def __init__(self):
        self._mongoClient: MongoClient
        self.db: Database
        self.connect()
        self.col: Collection

    def delete_from_id(self, _id: ObjectId):
        return self.col.delete_one({
            '_id': _id
        })

    def connect(self):
        self._mongoClient = MongoClient(
            host=MONGO_HOST,
            port=int(MONGO_PORT),
            username=MONGO_USERNAME, password=MONGO_PASSWORD,
            connect=False
        )
        self.db = self._mongoClient[MONGO_DBNAME]

    def get_collection(self, name: str) -> Collection:
        return self.db.get_collection(name)


mongo = Mongo()
