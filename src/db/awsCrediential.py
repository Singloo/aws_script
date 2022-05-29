from .mongo import Mongo
from bson.objectid import ObjectId
from src.types import AwsCrediential
from .exceptions import ExceedMaximumNumber
from .helper import ensure_decrypted, is_int
from functools import partial


class AwsCredientialRepo(Mongo):
    @property
    @classmethod
    def instance(cls):
        pass

    def __init__(self):
        super().__init__()
        self.col = self.get_collection('awsCrediential')

    def find_all(self, user_id: str) -> list[AwsCrediential]:
        cursor = self.col.find({'user_id': ObjectId(user_id)}).sort({
            'created_at': -1
        })
        return map(partial(ensure_decrypted, keys_to_decrypt=['aws_access_key_id', 'aws_secret_access_key']), list(cursor))

    def insert(self, doc: AwsCrediential, user_id: str) -> tuple[ObjectId, str]:
        existing = self.col.count_documents({
            'user_id': ObjectId(user_id)
        })
        if existing > 100:
            raise ExceedMaximumNumber
        alias: str = '1'
        if existing > 0:
            cursor = self.col.find().sort({
                'alias': -1
            })
            for doc in cursor:
                if is_int(doc['alias']):
                    alias = str(int(doc['alias']) + 1)
                    break
        res = self.col.insert_one(
            self.add_created_updated_at(
                {**doc, 'user_id': ObjectId(user_id), 'alias': alias})
        )
        return res.inserted_id, alias

    def find_by_id(self, _id: ObjectId) -> AwsCrediential:
        res = super().find_by_id(_id)
        return ensure_decrypted(res, ['aws_access_key_id', 'aws_secret_access_key']) if res != None else None

    def find_by_alias(self, user_id: str, alias: str):
        res: AwsCrediential = super().find_by_alias(user_id, alias)
        return ensure_decrypted(res, ['aws_access_key_id', 'aws_secret_access_key']) if res != None else None
