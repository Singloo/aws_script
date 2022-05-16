from typing import Any
from . import AsyncBaseMessageHandler
from .awsHandler import AwsHandler
from .ec2Handler import Ec2Handler

def destruct_msg(msg: str) -> list[str]:
    return msg.lower().strip().split(' ')


class InputMapperEntry(AsyncBaseMessageHandler):
    @property
    def aws(self):
        return AwsHandler(self.params)

    @property
    def ec2(self):
        return Ec2Handler(self.params)
