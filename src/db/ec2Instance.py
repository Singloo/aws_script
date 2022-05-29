from .mongo import Mongo
from src.types import Ec2Instance
from bson.objectid import ObjectId
from .exceptions import ExceedMaximumNumber
from .helper import ensure_decrypted, is_int


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
            {**doc, 'user_id': ObjectId(user_id), 'alias': alias, 'default': alias == 1})
        return res.inserted_id

    def find_by_id(self, _id: ObjectId) -> Ec2Instance:
        res = super().find_by_id(_id)
        return ensure_decrypted(res, ['instance_id']) if res != None else None

    def find_by_alias(self, user_id: str, alias: str):
        res: Ec2Instance = super().find_by_alias(user_id, alias)
        return ensure_decrypted(res, ['instance_id']) if res != None else None
