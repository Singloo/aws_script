from .mongo import Mongo
from bson.objectid import ObjectId
from src.types.type import Ec2Status
from pymongo.results import UpdateResult


class Ec2StatusRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2Status')

    def upsert_ec2_status(self, ec2_id: ObjectId, status: str, command: str, ip: str, user_id: ObjectId):
        doc = {
            'ec2_id': ec2_id,
            'status': status,
            'ip': ip,
            'last_command': command,
            'modified_by': user_id
        }
        res = self.col.find_one({
            'ec2_id': ec2_id,
            'active': True
        })
        if res is None:
            self.col.insert_one(self.add_created_updated_at(doc))
        else:
            self.col.update_one({
                'ec2_id': ec2_id
            }, {
                '$set': self.add_updated_at(doc)
            })

    def get_ec2_status(self, ec2_id: ObjectId) -> Ec2Status:
        return self.col.find_one({
            'ec2_id': ec2_id,
            'active': True
        })

    def update_status(self, ec2_id: ObjectId, status: str, ip: str | None = None):
        next_doc = {'status': status}
        if ip is not None:
            next_doc['ip'] = ip
        res: UpdateResult = self.col.update_one({
            'ec2_id': ec2_id,
        }, {
            '$set': self.add_updated_at(next_doc)
        })
        return res.modified_count
