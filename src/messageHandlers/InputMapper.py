from typing import Any
from . import AsyncBaseMessageHandler
from .awsHandler import AwsHandler
from .ec2Handler import Ec2Handler
from src.db.redis import CacheKeys
from .InputValidator import ValidatorManager, NoSuchSession


def destruct_msg(msg: str) -> list[str]:
    return msg.lower().strip().replace('_', '').split(' ')


class InputMapperEntry(AsyncBaseMessageHandler):
    @property
    def aws(self):
        return AwsHandler(self.params)

    @property
    def ec2(self):
        return Ec2Handler(self.params)

    async def _tryAwsBind(self):
        try:
            session = ValidatorManager.load_validator(
                CacheKeys.aws_validator_key(self.params.get('user_id')))
            return await self.aws.bind(self.params.get('origin_input'))
        except NoSuchSession:
            return None

    async def _fallback(self, cmds: list[str]):
        res1 = await self._tryAwsBind()
        if res1:
            return res1
