from asyncio.log import logger
from typing import Any
from . import AsyncBaseMessageHandler
from .awsHandler import AwsHandler
from .ec2Handler import Ec2Handler
from src.db.redis import CacheKeys
from .InputValidator import ValidatorManager, NoSuchSession
from datetime import datetime
from src.db.commandLog import CommandLogRepo
from .exceptions import InvalidCmd, NoSuchHandler
import traceback


def destruct_msg(msg: str) -> list[str]:
    return msg.lower().strip().replace('_', '').split(' ')


class InputMapperEntry(AsyncBaseMessageHandler):

    async def __call__(self, cmds: list[str]):
        started_at = datetime.now()
        err: Exception = None
        trace_info: str = None
        try:
            res = await super().__call__(cmds)
            CommandLogRepo().finish(
                self.params['origin_input'], self.user_id, started_at, datetime.now(), res)
            return res
        except NoSuchHandler as e:
            err = e
            return 'What?'
        except InvalidCmd as e:
            err = e
            return '\n'.join(e.args)
        except Exception as e:
            err = e
            trace_info = traceback.format_exc()
            logger.error(trace_info)
            return f'Unexpected error: {e.args}'
        finally:
            if err is None:
                return
            CommandLogRepo().error(
                self.params['origin_input'], self.user_id, started_at, datetime.now(), str(err), trace_info)

    @property
    def aws(self):
        return AwsHandler(self.params)

    @property
    def ec2(self):
        return Ec2Handler(self.params)

    async def _tryBind(self):
        aws_cache_key = CacheKeys.aws_validator_key(self.user_id)
        ec2_cache_key = CacheKeys.ec2_validator_key(self.user_id)
        inputs = self.params['origin_input'].split(' ')
        try:
            await ValidatorManager.load_validator(aws_cache_key)
            return await self.aws.bind(inputs)
        except NoSuchSession:
            try:
                await ValidatorManager.load_validator(ec2_cache_key)
                return await self.ec2.bind(inputs)
            except NoSuchSession:
                raise NoSuchHandler

    async def _fallback(self, cmds: list[str]):
        res1 = await self._tryBind()
        if res1:
            return res1
