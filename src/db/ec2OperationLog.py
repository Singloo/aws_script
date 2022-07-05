from .mongo import Mongo
from src.types.type import Ec2OperationLog
from .user import UserRepo
from bson.objectid import ObjectId
from datetime import datetime

MAX_RUNTIME = {
    'start': 60*5,
    'status': 20,
    'stop': 60
}


class Ec2OperationLogRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('ec2OperationLog')
        self.userRepo = UserRepo()

    def insert(self, ec2_id: ObjectId, cmd: str, user_id: ObjectId) -> ObjectId:
        doc: Ec2OperationLog = {'ec2_id': ec2_id,
                                'command': cmd,
                                'triggered_by': user_id,
                                'status': 'pending',
                                'started_at': datetime.now(),
                                'finished_at': None,
                                'success': False}
        res = self.col.insert_one(self.add_created_updated_at(doc))
        return res.inserted_id

    def fail_operation(self, _id: ObjectId):
        '''
            exceed max run time
        '''
        self.col.update_one({
            '_id': _id
        }, {
            '$set': {
                'status': 'exceed_max_runtime',
                'finished_at': datetime.now()
            }
        })

    def error_operation(self, _id: ObjectId, error):
        '''
            encountered error
        '''
        self.col.update_one({
            '_id': _id
        }, {
            '$set': {
                'status': 'error',
                'finished_at': datetime.now(),
                'error': str(error)
            }
        })

    def timeout_finish_operation(self, _id: ObjectId):
        '''
            didnt finish in time
        '''
        self.col.update_one({
            '_id': _id
        }, {
            '$set': {
                'status': 'timeout',
                'finished_at': datetime.now(),
                'success': True
            }
        })

    def finish_operation(self, _id: ObjectId):
        '''
            finished in time
        '''
        self.col.update_one({
            '_id': _id
        }, {
            '$set': {
                'status': 'success',
                'finished_at': datetime.now(),
                'success': True
            }
        })

    def get_last_unfinished_cmd(self, ec2_id: ObjectId) -> None | Ec2OperationLog:
        cursor = self.col.find({
            'ec2_id': ec2_id,
            'success': False,
            'status': 'pending'
        }).sort([('started_at', -1)])
        unfinshed_cmds: list[Ec2OperationLog] = []
        for operation_log in cursor:
            operation_log: Ec2OperationLog
            max_runtime = MAX_RUNTIME[operation_log['command']]
            if datetime.timestamp(operation_log['started_at']) + max_runtime < datetime.now().timestamp():
                # exceed max run time, set success to false
                self.fail_operation(operation_log['_id'])
            else:
                unfinshed_cmds.append(operation_log)
        if len(unfinshed_cmds) == 0:
            return None

        for operation_log in unfinshed_cmds[1:]:
            self.fail_operation(operation_log['_id'])

        return unfinshed_cmds[0]
