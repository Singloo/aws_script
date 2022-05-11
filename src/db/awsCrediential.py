from .mongo import Mongo
from bson.objectid import ObjectId
from src.types import AwsCrediential


class AwsCredientialRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('awsCrediential')

    def insert(self, doc: AwsCrediential) -> ObjectId:
        res = self.col.insert_one(doc)
        return res.inserted_id

    def delete_with_id(self, _id: str):
        self.col.delete_one({
            '_id': ObjectId(_id)
        })
