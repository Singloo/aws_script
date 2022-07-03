from typing import Any
from . import AsyncBaseMessageHandler
from .awsHandler import AwsHandler
from .ec2Handler import Ec2Handler
from src.db.redis import CacheKeys
from .InputValidator import ValidatorManager, NoSuchSession
from datetime import datetime
from src.db.commandLog import CommandLogRepo


def destruct_msg(msg: str) -> list[str]:
    return msg.lower().strip().replace('_', '').split(' ')


class InputMapperEntry(AsyncBaseMessageHandler):

    async def __call__(self, cmds: list[str]):
        started_at = datetime.now()
        try:
            res = await super().__call__(cmds)
            CommandLogRepo().finish(
                self.params['origin_input'], self.user_id, started_at, datetime.now(), res)
            return res
        except Exception as e:
            CommandLogRepo().error(
                self.params['origin_input'], self.user_id, started_at, datetime.now(), e)
            raise e

    @property
    def aws(self):
        return AwsHandler(self.params)

    @property
    def ec2(self):
        return Ec2Handler(self.params)

    async def _tryAwsBind(self):
        try:
            session = await ValidatorManager.load_validator(
                CacheKeys.aws_validator_key(self.params.get('user_id')))
            return await self.aws.bind(self.params.get('origin_input'))
        except NoSuchSession:
            return None

    async def _fallback(self, cmds: list[str]):
        res1 = await self._tryAwsBind()
        if res1:
            return res1
