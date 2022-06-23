from typing import Any
from .mongo import Mongo
from src.types.type import Ec2CronLog
from bson.objectid import ObjectId
from datetime import datetime


class Ec2CronLogRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2CronLog')

    def insert(self, cron_id: ObjectId, command: str):
        return self.col.insert_one(self.add_created_updated_at({
            'cron_id': cron_id,
            'command': command,
            'started_at': datetime.now(),
            'success': False
        })).inserted_id

    def finish(self, _id: ObjectId, result: str):
        return self.col.update_one({
            '_id': _id
        }, {
            '$set': {
                'success': True,
                'finished_at': datetime.now(),
                'result': result
            }
        })

    def error(self, _id: ObjectId, error: Any):
        return self.col.update_one({
            '_id': _id
        }, {
            '$set': {
                'error': error,
                'finished_at': datetime.now()
            }
        })
