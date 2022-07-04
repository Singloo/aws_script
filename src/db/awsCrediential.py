from .mongo import Mongo
from bson.objectid import ObjectId
from src.types import AwsCrediential
from .exceptions import ExceedMaximumNumber
from .helper import ensure_decrypted, is_int
from functools import partial
from pymongo import IndexModel


class AwsCredientialRepo(Mongo):
    @property
    @classmethod
    def instance(cls):
        pass

    def __init__(self):
        super().__init__()
        self.col = self.get_collection('awsCrediential')
        self.create_indexes()

    def create_indexes(self):
        index_models = [IndexModel(
            [('alias', 1)],  background=True)]
        self.col.create_indexes(index_models)

    def find_all(self, user_id: ObjectId) -> list[AwsCrediential]:
        cursor = self.col.find({'user_id': user_id, 'active': True}).sort(
            [('created_at', -1)])
        return list(map(partial(ensure_decrypted, keys_to_decrypt=['aws_access_key_id', 'aws_secret_access_key']), list(cursor)))

    def insert(self, doc: AwsCrediential, user_id: ObjectId) -> tuple[ObjectId, str]:
        existing = self.col.count_documents({
            'user_id': user_id
        })
        if existing > 100:
            raise ExceedMaximumNumber
        alias: str = self.get_alias(user_id)
        res = self.col.insert_one(
            self.add_created_updated_at(
                {**doc, 'user_id': user_id, 'alias': alias, 'active': True})
        )
        return res.inserted_id, alias

    def find_by_id(self, _id: ObjectId) -> AwsCrediential:
        res = super().find_by_id(_id)
        return ensure_decrypted(res, ['aws_access_key_id', 'aws_secret_access_key']) if res != None else None

    def find_by_alias(self, user_id: ObjectId, alias: str):
        res: AwsCrediential = super().find_by_alias(user_id, alias)
        return ensure_decrypted(res, ['aws_access_key_id', 'aws_secret_access_key']) if res != None else None
