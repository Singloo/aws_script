from .mongo import Mongo
from src.types import Ec2Instance
from bson.objectid import ObjectId
from .exceptions import ExceedMaximumNumber


class Ec2InstanceRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2Instance')

    def insert(self, doc: Ec2Instance, user_id: str) -> ObjectId:
        existing = self.col.count_documents({
            'user_id': ObjectId(user_id)
        })
        if existing > 100:
            raise ExceedMaximumNumber
        alias = str(existing+1)
        res = self.col.insert_one(
            {**doc, 'user_id': ObjectId(user_id), 'alias': alias, 'default': alias == 1})
        return res.inserted_id
