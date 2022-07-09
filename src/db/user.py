from .mongo import Mongo
from src.types import User
from bson.objectid import ObjectId
from datetime import datetime


class UserRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('user')

    def insert(self, doc: User) -> ObjectId:
        res = self.col.insert_one(
            {**self.add_created_updated_at(doc), 'activated_at': datetime.now()})
        return res.inserted_id

    def find_by_wechat_id(self, wechat_id: str) -> ObjectId:
        doc = {
            'wechat_id': wechat_id
        }
        res = self.col.find_one(doc)
        if res is None:
            return self.insert(doc)
        else:
            self.col.update_one(doc, {
                '$set': self.add_updated_at({'activated_at': datetime.now()})
            })
        return res['_id']
