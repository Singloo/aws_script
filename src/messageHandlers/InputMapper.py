from asyncio.log import logger
from typing import Any
from . import AsyncBaseMessageHandler
from .awsHandler import AwsHandler
from .ec2Handler import Ec2Handler, Ec2Start, Ec2Stop, Ec2StatusCmd
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
        replay_msg: str = None
        try:
            replay_msg = await super().__call__(cmds)
            CommandLogRepo().finish(
                self.params['origin_input'], self.user_id, started_at, datetime.now(), replay_msg)
            logger.info(f'[InputMapper 28] {replay_msg}')
        except NoSuchHandler as e:
            err = e
            replay_msg = 'What?'
        except InvalidCmd as e:
            err = e
            replay_msg = '\n'.join(e.args)
        except Exception as e:
            err = e
            trace_info = traceback.format_exc()
            logger.error(trace_info)
            replay_msg = f'Unexpected error: {e.args}'
        finally:
            if err != None:
                CommandLogRepo().error(
                    self.params['origin_input'], self.user_id, started_at, datetime.now(), str(err), trace_info)
            return replay_msg

    @property
    def aws(self):
        return AwsHandler(self.params)

    @property
    def ec2(self):
        return Ec2Handler(self.params)

    @property
    def start(self):
        return Ec2Start(self.params)

    @property
    def status(self):
        return Ec2StatusCmd(self.params)

    @property
    def state(self):
        return Ec2StatusCmd(self.params)

    @property
    def stop(self):
        return Ec2Stop(self.params)

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
