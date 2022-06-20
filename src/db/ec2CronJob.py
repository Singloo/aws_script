from .mongo import Mongo
from bson.objectid import ObjectId
from .exceptions import ExceedMaximumNumber
from src.types.type import Ec2Cron


class Ec2CronRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2Cron')

    def insert(self, instance_id: ObjectId, cmd: str, hour: int, minute: int, user_id: ObjectId):
        return self.col.insert_one(self.add_created_updated_at({
            'ec2_id': instance_id,
            'command': cmd,
            'hour': hour,
            'minute': minute,
            'created_by': user_id
        }))

    def find_by_time(self, instance_id: ObjectId, cmd: str, hour: int, minute: int) -> Ec2Cron | None:
        return self.col.find_one({
            'ec2_id': instance_id,
            'commnand': cmd,
            'hour': hour,
            'minute': minute
        })
