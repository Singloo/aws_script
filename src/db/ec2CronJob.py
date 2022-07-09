from .mongo import Mongo
from bson.objectid import ObjectId
from .exceptions import ExceedMaximumNumber
from src.types.type import Ec2Cron
from pymongo import IndexModel


class Ec2CronRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2Cron')
        self.create_indexes()

    def create_indexes(self):
        index_models = [IndexModel(
            [('alias', 1)], background=True)]
        self.col.create_indexes(index_models)

    def insert(self, ec2_id: ObjectId, cmd: str, hour: int, minute: int, user_id: ObjectId):
        alias = self.get_alias(user_id)
        return self.col.insert_one(self.add_created_updated_at({
            'ec2_id': ec2_id,
            'command': cmd,
            'hour': hour,
            'minute': minute,
            'user_id': user_id,
            'running': False,
            'alias': alias,
            'active': False
        })).inserted_id, alias

    def job_run(self, _id: ObjectId, job_id: str):
        return self.col.update_one({
            '_id': _id
        }, {
            '$set': self.add_updated_at({
                'running': True,
                'active': True,
                'job_id': job_id
            })
        }).modified_count > 0

    def find_by_time(self, ec2_id: ObjectId, cmd: str, hour: int, minute: int) -> Ec2Cron | None:
        return self.col.find_one({
            'ec2_id': ec2_id,
            'command': cmd,
            'hour': hour,
            'minute': minute,
        })

    def find_all(self, user_id: ObjectId):
        cursor = self.col.find({'user_id': user_id}).sort(
            [('created_at', -1)])
        return list(cursor)

    def find_by_alias(self, user_id: ObjectId, alias: str):
        res = self.col.find_one({
            'user_id': user_id,
            'alias': alias,
        })
        return res

    def activate(self, _id: ObjectId, job_id: str):
        return self.col.update_one({
            '_id': _id
        }, {
            '$set': self.add_updated_at({
                'active': True,
                'running': True,
                'job_id': job_id
            })
        })

    def deactivate(self, _id: ObjectId):
        return self.col.update_one({
            '_id': _id
        }, {
            '$set': self.add_updated_at({
                'active': False,
                'running': False
            })
        })

    def rm_by_ec2_ids(self, ids: list[ObjectId]):
        return self.col.delete_many({
            'ec2_id': {'$in': ids}
        }).deleted_count

    def find_by_ec2_ids(self, ids: list[ObjectId]):
        return self.col.find({
            'ec2_id': {'$in': ids}
        })
