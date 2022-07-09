from asyncio.log import logger
from typing import Any
from . import AsyncBaseMessageHandler
from .awsHandler import AwsBind, AwsList, AwsRm, AwsDefault
from .ec2Handler import Ec2Start, Ec2Stop, Ec2StatusCmd, Ec2CronCmd, Ec2Bind, Ec2Alias, Ec2List, Ec2Rm, Ec2Default
from src.db.redis import CacheKeys
from .InputValidator import ValidatorManager, NoSuchSession
from datetime import datetime
from src.db.commandLog import CommandLogRepo
from .exceptions import InvalidCmd, NoSuchHandler
import traceback
from .doc import Help


class AwsHandler(AsyncBaseMessageHandler):
    @property
    def bind(self):
        return AwsBind(self.params)

    @property
    def list(self):
        return AwsList(self.params)

    @property
    def rm(self):
        return AwsRm(self.params)

    @property
    def default(self):
        return AwsDefault(self.params)


class Ec2Handler(AsyncBaseMessageHandler):
    @property
    def bind(self):
        return Ec2Bind(self.params)

    @property
    def list(self):
        return Ec2List(self.params)

    @property
    def rm(self):
        return Ec2Rm(self.params)

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

    @property
    def alias(self):
        return Ec2Alias(self.params)

    @property
    def cron(self):
        return Ec2CronCmd(self.params)

    @property
    def default(self):
        return Ec2Default(self.params)


class InputMapperEntry(AsyncBaseMessageHandler):

    async def __call__(self, cmds: list[str]):
        started_at = datetime.now()
        err: Exception = None
        trace_info: str = None
        reply_msg: str = None
        try:
            reply_msg = await super().__call__(cmds)
            CommandLogRepo().finish(
                self.params['origin_input'], self.user_id, started_at, datetime.now(), reply_msg)
        except NoSuchHandler as e:
            err = e
            reply_msg = 'What?'
        except InvalidCmd as e:
            err = e
            reply_msg = '\n'.join(e.args)
        except Exception as e:
            err = e
            trace_info = traceback.format_exc()
            logger.error(trace_info)
            reply_msg = f'Unexpected error: {e.args}'
        finally:
            if err != None:
                CommandLogRepo().error(
                    self.params['origin_input'], self.user_id, started_at, datetime.now(), str(err), trace_info)
            return reply_msg

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

    @property
    def help(self):
        return Help(self.params)

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
