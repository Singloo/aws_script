from .mongo import Mongo
from bson.objectid import ObjectId
from src.types import AwsCrediential
import src.utils.crypto as Crypto
from .exceptions import ExceedMaximumNumber


class AwsCredientialRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('awsCrediential')

    def insert(self, doc: AwsCrediential, user_id: str) -> ObjectId:
        existing = self.col.count_documents({
            'user_id': ObjectId(user_id)
        })
        if existing > 100:
            raise ExceedMaximumNumber
        res = self.col.insert_one({**doc, 'user_id': ObjectId(user_id)})
        return res.inserted_id

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
