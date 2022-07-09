from datetime import datetime
from typing import Any
from .mongo import Mongo
from bson.objectid import ObjectId


class CommandLogRepo(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('commandLog')

    def finish(self, command: str, triggered_by: ObjectId, started_at: datetime, finished_at: datetime, result: str):
        return self.col.insert_one(self.add_created_updated_at({
            'command': command,
            'triggered_by': triggered_by,
            'started_at': started_at,
            'finished_at': finished_at,
            'result': result,
            'success': True
        }))

    def error(self, command: str, triggered_by: ObjectId, started_at: datetime, finished_at: datetime, error: Any, trace_info: str | None = None):
        return self.col.insert_one(self.add_created_updated_at({
            'command': command,
            'triggered_by': triggered_by,
            'started_at': started_at,
            'finished_at': finished_at,
            'error': str(error),
            'success': False,
            'trace_info': trace_info
        }))
