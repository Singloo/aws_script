from .mongo import Mongo
from bson.objectid import ObjectId
from src.types import AwsCrediential
import src.utils.crypto as Crypto
from .exceptions import ExceedMaximumNumber


def _try_decrypt(data: AwsCrediential) -> AwsCrediential:
    if data['encrypted'] == False:
        return data
    return {
        **data,
        'aws_access_key_id': Crypto.decrypt(data['aws_access_key_id']),
        'aws_secret_access_key': Crypto.decrypt(data['aws_secret_access_key'])
    }


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
        return map(_try_decrypt, list(cursor))

    def insert(self, doc: AwsCrediential, user_id: str) -> tuple[ObjectId, str]:
        existing = self.col.count_documents({
            'user_id': ObjectId(user_id)
        })
        if existing > 100:
            raise ExceedMaximumNumber
        alias = str(existing+1)
        res = self.col.insert_one(
            self.add_created_updated_at(
                {**doc, 'user_id': ObjectId(user_id), 'alias': alias})
        )
        return res.inserted_id, alias

    def find_by_id(self, _id: ObjectId) -> AwsCrediential:
        res: AwsCrediential = self.col.find_one({
            '_id': _id
        })
        if res is None:
            return None
        return _try_decrypt(res)

    def find_by_alias(self, user_id: str, alias: str):
        res: AwsCrediential = self.col.find_one({
            'user_id': ObjectId(user_id),
            'alias': alias
        })
        return None if res is None else _try_decrypt(res)
