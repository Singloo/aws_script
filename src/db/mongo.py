from pymongo import MongoClient
from pymongo.database import Database, Collection
from src.utils.constants import MONGO_DBNAME, MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USERNAME
from bson.objectid import ObjectId
from typing_extensions import Self
from datetime import datetime


class Mongo(object):
    __instance: Self

    def __new__(cls: type[Self]) -> Self:
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self):
        self._mongoClient: MongoClient
        self.db: Database
        self.connect()
        self.col: Collection

    def delete_from_id(self, _id: ObjectId):
        return self.col.delete_one({
            '_id': _id
        })

    def add_created_updated_at(self, doc: dict):
        return {**doc, 'created_at': datetime.now(), 'updated_at': datetime.now()}

    def add_updated_at(self, doc: dict):
        return {**doc, 'updated_at': datetime.now()}

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


    def find_by_id(self, _id: ObjectId):
        if not isinstance(_id, ObjectId):
            _id = ObjectId(_id)
        res = self.col.find_one({
            '_id': _id
        })
        return res

    def find_by_alias(self, user_id: str, alias: str):
        res = self.col.find_one({
            'user_id': ObjectId(user_id),
            'alias': alias
        })
        return res

    def find_by_vague_id(self, identifier: str):
        is_object_id = ObjectId.is_valid(identifier)
        find_instance = self.find_by_id if is_object_id else self.find_by_alias
        args = (ObjectId(identifier),) if is_object_id else (
            self.params['user_id'], identifier)
        res = find_instance(*args)
        return res