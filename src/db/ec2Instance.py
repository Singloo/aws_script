from .mongo import Mongo
from src.types import Ec2Instance
from bson.objectid import ObjectId


class Ec2InstanceRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2Instance')

    def insert(self, doc: Ec2Instance) -> ObjectId:
        res = self.col.insert_one(doc)
        return res.inserted_id

