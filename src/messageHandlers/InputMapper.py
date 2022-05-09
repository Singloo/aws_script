from typing import Any
from . import BaseMessageHandler
from .awsHandler import AwsHandler
from .ec2Handler import Ec2Handler
def destruct_msg(msg: str) -> list[str]:
    return msg.lower().strip().split(' ')


class InputMapperEntry(BaseMessageHandler):
    aws = AwsHandler
    ec2 = Ec2Handler