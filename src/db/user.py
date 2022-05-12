from .mongo import Mongo
from src.types import User
from bson.objectid import ObjectId


class UserRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('user')

    def insert(self, doc: User) -> ObjectId:
        res = self.col.insert_one(doc)
        return res.inserted_id

