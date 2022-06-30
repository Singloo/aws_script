from .mongo import Mongo
from bson.objectid import ObjectId
from .exceptions import ExceedMaximumNumber
from src.types.type import Ec2Cron
from pymongo import IndexModel


class Ec2CronRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2Cron')

    def create_indexes(self):
        index_models = [IndexModel(
            [('alias', 1)], unique=True, sparse=True, background=True)]
        self.col.create_indexes(index_models)

    def insert(self, instance_id: ObjectId, cmd: str, hour: int, minute: int, user_id: ObjectId):
        alias = self.get_alias(user_id)
        return self.col.insert_one(self.add_created_updated_at({
            'ec2_id': instance_id,
            'command': cmd,
            'hour': hour,
            'minute': minute,
            'user_id': user_id,
            'running': False,
            'alias': alias,
        })).inserted_id, alias

    def run_job(self, _id: ObjectId, job_id: str):
        return self.col.update_one({
            '_id': _id
        }, {
            '$set': {
                'running': True,
                'job_id': job_id
            }
        }).modified_count > 0

    def find_by_time(self, instance_id: ObjectId, cmd: str, hour: int, minute: int) -> Ec2Cron | None:
        return self.col.find_one({
            'ec2_id': instance_id,
            'commnand': cmd,
            'hour': hour,
            'minute': minute,
            'active': True,
            'running': True
        })

    def find_all(self, user_id: ObjectId):
        cursor = self.col.find({'user_id': user_id}).sort({
            'created_at': -1
        })
        return list(cursor)
