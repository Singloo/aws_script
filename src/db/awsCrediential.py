from .mongo import Mongo
from bson.objectid import ObjectId
from src.types import AwsCrediential
import src.utils.crypto as Crypto
from .exceptions import ExceedMaximumNumber


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
        return list(cursor)

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
        if res['encrypted']:
            return {
                **res,
                'aws_access_key_id': Crypto.decrypt(res['aws_access_key_id']),
                'aws_secret_access_key': Crypto.decrypt(res['aws_secret_access_key'])
            }
        return res
