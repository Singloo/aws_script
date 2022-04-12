from pymongo import MongoClient
from pymongo.database import Database
from src.utils.constants import MONGO_DBNAME, MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USERNAME


class Mongo(object):
    def __init__(self):
        self._mongoClient: MongoClient
        self._db: Database
        self.connect()

    def connect(self):
        self._mongoClient = MongoClient(
            host=MONGO_HOST,
            port=int(MONGO_PORT),
            username=MONGO_USERNAME, password=MONGO_PASSWORD,
            connect=False
        )
        self._db = self.mongoClient[MONGO_DBNAME]
