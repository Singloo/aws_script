from .mongo import Mongo
from src.types import Ec2Instance
from bson.objectid import ObjectId
from .exceptions import ExceedMaximumNumber
from .helper import ensure_decrypted, is_int
from functools import partial
from pymongo import IndexModel


class Ec2InstanceRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2Instance')
        self.create_indexes()

    def create_indexes(self):
        index_models = [IndexModel(
            [('alias', 1)],  background=True)]
        self.col.create_indexes(index_models)

    def insert(self, doc: Ec2Instance, user_id: ObjectId) -> ObjectId:
        existing = self.col.count_documents({
            'user_id': user_id
        })
        if existing > 100:
            raise ExceedMaximumNumber
        alias = self.get_alias(user_id)
        res = self.col.insert_one(
            {**doc, 'user_id': user_id, 'alias': alias, 'default': alias == 1})
        return res.inserted_id

    def find_by_id(self, _id: ObjectId) -> Ec2Instance:
        res = super().find_by_id(_id)
        return ensure_decrypted(res, ['instance_id']) if res != None else None

    def find_by_alias(self, user_id: ObjectId, alias: str):
        res: Ec2Instance = super().find_by_alias(user_id, alias)
        return ensure_decrypted(res, ['instance_id']) if res != None else None

    def update_alias(self, _id: ObjectId, user_id: ObjectId, newAlias: str):
        res = super().find_by_alias(user_id, newAlias)
        if res != None:
            return False
        self.col.update_one(
            {'_id': _id}, {'$set': self.add_updated_at({'alias': newAlias})})
        return True

    def get_default(self):
        return self.col.find_one({
            'default': True
        })

    def find_all(self, user_id: ObjectId) -> list[Ec2Instance]:
        cursor = self.col.find({'user_id': user_id, 'active': True}).sort([{
            'created_at': -1
        }])
        return list(map(partial(ensure_decrypted, keys_to_decrypt=['instance_id']), list(cursor)))
