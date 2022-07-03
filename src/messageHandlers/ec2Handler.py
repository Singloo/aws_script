import re
from src.logger import logger
from src.db.redis import CacheKeys
from src.db.exceptions import ExceedMaximumNumber
from src.types.type import Ec2Instance
from . import AsyncBaseMessageHandler
from .InputValidator import ValidatorManager, Validator, SessionExpired, ValidatorInvalidAndExceedMaximumTimes, ValidatorInvalidInput, SessionFinished, NoSuchSession
from .exceptions import InvalidCmd
from src.db.awsCrediential import AwsCredientialRepo
from src.db.ec2Instance import Ec2InstanceRepo
from src.db.ec2CronJob import Ec2CronRepo
from src.utils.util import re_strict_match, desensitize_data
from functools import partial
from .helper import test_aws_resource
from .messageGenerator import MessageGenerator
from src.schedulers.scheduler import sched
from apscheduler.job import Job
from .ec2HandlerHelper import validate_outline, cmd_executor, ec2_start, ec2_status, ec2_stop, ec2_cron_validate_and_transform_params, cmd_executor_sync
from typing import List

EC2_VALIDATORS = [
    Validator(
        prompt='Please input ec2 instance id, e.g. i-03868cxxxxfec037',
        invalid_prompt='Invalid instance id',
        attribute_name='instance_id',
        validator=partial(re_strict_match, pattern=r'^i-[a-z0-9]{17,20}$'),
        encrypt=True
    ),
    Validator(
        prompt='Awesome, please input outline token(optional), if you want to skip this step, please input: skip',
        invalid_prompt='Invalid outline token',
        attribute_name='outline_token',
        validator=validate_outline
    )
]


class Ec2Bind(AsyncBaseMessageHandler):
    def __transform_outline_token(self, token: str):
        if token.lower().strip() == 'skip':
            return {
                'outline_token': None,
                'outline_port': None,
            }
        token = token.split('?')[0]
        match = re.search(r':(\d{4,5})\??', token)
        return {
            'outline_token': token,
            'outline_port': None if match is None else match.groups()[0]
        }

    async def __call__(self, cmds: list[str]):
        uniq_key = CacheKeys.ec2_validator_key(self.params.get('user_id'))
        if len(cmds) != 1:
            raise InvalidCmd(
                'ec2 bind: invalid input, expect aws credential id or alias provided')
        try:
            vm: ValidatorManager
            try:
                vm = await ValidatorManager.load_validator(uniq_key)
                return await vm.next(cmds[0])
            except NoSuchSession:
                identifier = cmds[0]
                ins = AwsCredientialRepo().find_by_vague_id(identifier, self.user_id)
                if ins is None:
                    raise InvalidCmd(
                        'ec2 bind: invalid input, no such aws crediential')
                vm = ValidatorManager.init_db_input_validator(
                    EC2_VALIDATORS, uniq_key, col_name='ec2Instance', aws_crediential_id=ins['_id'])
                return await vm.next()

        except SessionFinished:
            vm = await ValidatorManager.load_validator(uniq_key)
            data = vm.collect()['data']
            aws_crediential_id = vm.collect(
            )['other_args']['aws_crediential_id']
            aws_crediential_ins = AwsCredientialRepo().find_by_id(aws_crediential_id)
            res = await test_aws_resource(
                aws_crediential_ins['region_name'], aws_crediential_ins['aws_access_key_id'], aws_crediential_ins['aws_secret_access_key'], instance_id=data['instance_id'])
            if isinstance(res, str):
                return res
            object_id, alias = Ec2InstanceRepo().insert(
                {**data, **self.__transform_outline_token(
                    data['outline_token']), 'encrypted': True},
                self.params.get('user_id')
            )
            return f'Success, your credientials are encrypted well in our database.\n [ID]: {object_id} \n[Default Alias]:{alias}'
        except ValidatorInvalidAndExceedMaximumTimes:
            return 'Invalid input and exceed maximum retry times, please try again.'
        except ValidatorInvalidInput:
            return 'Invalid input'
        except SessionExpired:
            return 'Ec2 bind: Sorry, session is expired, please try again.'
        except ExceedMaximumNumber:
            return 'Sorry, you cannot bind more ec2 instance(maximum 100)'


class Ec2List(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        user_id = self.params['user_id']
        inss = Ec2InstanceRepo().find_all(user_id)
        if len(inss) == 0:
            return 'No result\nLets start by [ec2 bind]'
        msgGen = MessageGenerator().list_header('Ec2 list', len(inss))
        for ins in inss:
            ins['instance_id'] = desensitize_data(
                ins["instance_id"], 4, 4)
            msgGen.list_item(ins)
        return msgGen.generate()


class Ec2Rm(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) != 1:
            raise InvalidCmd('ec2 rm: invalid input, expect id or alias')
        identifier = cmds[0]
        repo = Ec2InstanceRepo()
        ins = repo.find_by_vague_id(identifier, self.user_id)
        if ins is None:
            return 'No such instance'
        repo.delete_from_id(ins['_id'])
        return f'Success, instance: {identifier} has been removed.'


class Ec2Start(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return cmd_executor(cmds, 'start', 'stopped', self.user_id, ec2_start)


class Ec2StatusCmd(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return cmd_executor(cmds, 'status', None, self.user_id, ec2_status)


class Ec2Stop(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return cmd_executor(cmds, 'stop', 'running', self.user_id, ec2_stop)


class Ec2Alias(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) > 2:
            raise InvalidCmd(
                'ec2 alias: invalid input, expect <id | alias > <new alias>')
        identifier, newAlias = cmds
        repo = Ec2InstanceRepo()
        ins: Ec2Instance = repo.find_by_vague_id(identifier, self.user_id)
        if ins is None:
            return 'No such instance'
        success = repo.update_alias(
            ins['_id'], self.params['user_id'], newAlias)
        if success:
            return 'Success'
        return f'Alias: {newAlias} already existed'


class Ec2CronList(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        user_id = self.user_id
        inss = Ec2CronRepo().find_all(user_id)
        if len(inss) == 0:
            return 'No result\nLets start by [ec2 cron]'
        msgGen = MessageGenerator().list_header('Ec2 cron list', len(inss))
        for ins in inss:
            msgGen.list_item(ins)
        return msgGen.generate()


class Ec2CronRm(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) != 1:
            raise InvalidCmd('ec2 cron rm: invalid input, expect id or alias')
        identifier = cmds[0]
        repo = Ec2CronRepo()
        ins = repo.find_by_vague_id(identifier, self.user_id)
        if ins is None:
            return 'No such cron job'
        repo.delete_from_id(ins['_id'])
        return f'Success, cron job: {identifier} has been removed.'


class Ec2Cron(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        # check param length
        if len(cmds) not in [2, 3]:
            raise InvalidCmd(
                'ec2 cron: invalid input, expect [id | alias ] <cron string> <command> \ncron string: hour:minute e.g 23:30 hour:[0:23], minute:[0:59]\n command: start | stop')
        # validate each param
        instance, cron_time, _cmd = ec2_cron_validate_and_transform_params(
            cmds, self.user_id)
        hour, minute = cron_time
        # check if exists a same cron job
        existed = Ec2CronRepo().find_by_time(
            instance['_id'], _cmd, hour, minute)
        if existed is not None:
            return MessageGenerator().existed('cron job')
        # insert into db set running false
        ec2_cron_id, alias = Ec2CronRepo().insert(
            instance['_id'], _cmd, hour, minute, self.user_id)
        # schedule job
        CRON_PARAMS = {
            'start': ([instance['_id']],  'start', 'stopped', self.user_id, ec2_start),
            'stop': ([instance['_id']], 'stop', 'running', self.user_id, ec2_stop)
        }
        job: Job = sched.add_job(cmd_executor_sync, args=(
            ec2_cron_id, *CRON_PARAMS[_cmd]), trigger='cron', hour=hour, minute=minute)
        # set cron job to running
        Ec2CronRepo().run_job(ec2_cron_id, job.id)
        return f'Successfully added a cron job [ID] {ec2_cron_id} [Alias] {alias}'

    @property
    def list(self):
        return Ec2CronList(self.params)

    @property
    def rm(self):
        return Ec2CronRm(self.params)


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
        return Ec2Cron(self.params)
