import re
from src.logger import logger
from botocore.exceptions import ClientError
from src.db.redis import json_save, json_get, CacheKeys
from src.db.exceptions import ExceedMaximumNumber, NoSuchDocument
import asyncio
from typing import List, TYPE_CHECKING, Tuple
from src.types import CachedData
import aioboto3
from src.types.type import Ec2Instance, Ec2OperationLog, Ec2Status
from src.utils.constants import REGION_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, SS_PORT, SS_STR
from . import AsyncBaseMessageHandler
from .InputValidator import ValidatorManager, Validator, SessionExpired, ValidatorInvalidAndExceedMaximumTimes, ValidatorInvalidInput, SessionFinished, NoSuchSession
from .exceptions import InvalidCmd
from src.db.awsCrediential import AwsCredientialRepo
from src.db.ec2Instance import Ec2InstanceRepo
from src.utils.util import re_strict_match
from src.db.ec2OperationLog import Ec2OperationLogRepo
from src.db.ec2Status import Ec2StatusRepo
from functools import partial
import base64
from .helper import test_aws_resource
from .messageGenerator import MessageGenerator
from bson.objectid import ObjectId
from src.utils.util import async_race
from .ec2HandlerHelper import get_ins_state_and_ip, update_log_and_instance_status, create_and_schedule_status_task
from .ec2InstanceManager import getEc2Instance, getEc2InstanceWithCredentialId

if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
    from mypy_boto3_ec2.type_defs import StartInstancesResultTypeDef
else:
    EC2Client = object
    EC2ServiceResource = object
    Instance = object
    StartInstancesResultTypeDef = object


def _try_to_decrypt_outline_token(token: str):
    '''
    return False
    or [crypto method, password]
    '''
    match = re.search(r'ss:\/\/([a-zA-Z0-9]{45,}=?)@', token)
    if match is None:
        return False
    str1 = match.groups()[0]
    try:
        decoded = base64.b64decode(str1).decode('utf8').split(':')
        if len(decoded) != 2:
            return False
        return decoded
    except:
        return False


def validate_outline(input: str):
    '''
        check if a outline token is valid
    '''
    if input.strip().lower() == 'skip':
        return True
    token = input.split('?')[0]
    matched = re_strict_match(
        token, r'^ss:\/\/[a-zA-Z0-9]{45,}={1,2}@([0-9]{1,3}\.?){4}:[0-9]{2,5}$')
    if not matched:
        return False
    res = _try_to_decrypt_outline_token(token)
    return res is not False


EC2_VALIDATORS = [
    Validator(
        prompt='Please input ec2 instance id, e.g. i-03868cxxxxfec037',
        invalid_prompt='Invalid instance id',
        attribute_name='instance_id',
        validator=partial(re_strict_match, pattern=r'^i-[a-z0-9]{17,20}$'),
        encrypt=True
    ),
    Validator(
        prompt='Please input outline token(optional), if you want to skip this step, please input: skip',
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
        try:
            vm: ValidatorManager
            vm = ValidatorManager.load_validator(uniq_key)
            if vm is None:
                if len(cmds) != 1:
                    raise InvalidCmd(
                        'ec2 bind: invalid input, expect id or alias provided')
                identifier = cmds[0]
                ins = AwsCredientialRepo().find_by_vague_id(identifier)
                if ins is None:
                    raise InvalidCmd(
                        'ec2 bind: invalid input, no such aws crediential')
                vm = ValidatorManager.init_db_input_validator(
                    EC2_VALIDATORS, uniq_key, col_name='ec2Instance', aws_crediential_id=ins['_id'])
                return vm.next()
            return vm.next(cmds[0])

        except SessionFinished:
            vm = ValidatorManager.load_validator(uniq_key)
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
            return 'Sorry, session is expired, please try again.'
        except NoSuchSession:
            return 'No aws bind session, please try again'
        except ExceedMaximumNumber:
            return 'Sorry, you cannot bind more AWS crediential(maximum 100)'


class Ec2List(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 list')


class Ec2Rm(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) != 1:
            raise InvalidCmd('ec2 rm: invalid input, expect id or alias')
        identifier = cmds[0]
        repo = Ec2InstanceRepo()
        ins = repo.find_by_vague_id(identifier)
        if ins is None:
            return 'No such instance'
        repo.delete_from_id(ins['_id'])
        return f'Success, instance: {identifier} has been removed.'


def _get_ec2_instance(vague_id: str | None) -> Ec2Instance:
    if vague_id is None:
        return Ec2InstanceRepo().get_default()
    return Ec2InstanceRepo().find_by_vague_id(vague_id)


async def _ec2_start(instance_id: ObjectId, aws_crediential_id: ObjectId, ec2_log_id: ObjectId, user_id: ObjectId):
    async with getEc2InstanceWithCredentialId(instance_id, aws_crediential_id) as ins:
        try:
            ins_state = await ins.state
            prev_state = ins_state['Name']
            response: StartInstancesResultTypeDef = await ins.start()
            logger.info('[Instance successfully started]')
            curr_state = response['StartingInstances'][0]['CurrentState']['Name']
            update_log_and_instance_status(ec2_log_id, instance_id, curr_state)
            create_and_schedule_status_task(
                instance_id, aws_crediential_id, user_id, 'running')
            return curr_state
        except Exception as e:
            Ec2OperationLogRepo().error_operation(ec2_log_id, e)
            logger.error(
                f'[ec2 start error] instance_id: {instance_id} error: {e}')
            return MessageGenerator().cmd_error('start', e)


class Ec2Start(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) >= 2:
            raise InvalidCmd(MessageGenerator().invalid_cmd(
                'ec2 start', '<id | alias> or no input(The default Ec2 instance will be used)').generate())
        ec2_instance = _get_ec2_instance(None if len(cmds) == 0 else cmds[0])
        status: Ec2Status = Ec2StatusRepo().find_by_id(ec2_instance['_id'])
        repo = Ec2OperationLogRepo()
        unfinished_cmd = repo.get_last_unfinished_cmd()
        if unfinished_cmd is not None:
            unfinished_cmd: Ec2OperationLog
            cmd = unfinished_cmd['command']
            if cmd == 'start':
                return MessageGenerator().same_cmd_is_running(cmd, unfinished_cmd['started_at']).generate()
            return MessageGenerator().last_cmd_still_running(cmd, unfinished_cmd['started_at'], status['status']).generate()
        if status['status'] != 'stopped':
            return MessageGenerator().invalid_status_for_cmd('start', 'stopped', status['status']).generate()
        ec2_log_id = repo.insert(ec2_instance['_id'], 'start', self.user_id)
        try:
            current_status = await _ec2_start(
                ec2_instance['_id'], ec2_instance['aws_crediential_id'], ec2_log_id, self.user_id)
            return MessageGenerator().cmd_success('start', current_status).generate()
        except ClientError as e:
            repo.error_operation(ec2_log_id, e)
            return MessageGenerator().cmd_error('start', e)


class Ec2StatusCmd(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) >= 2:
            raise InvalidCmd(
                MessageGenerator().invalid_cmd(
                    'ec2 status', '<id | alias> or no input(The default Ec2 instance will be used)').generate())
        ec2_instance = _get_ec2_instance(None if len(cmds) == 0 else cmds[0])
        status: Ec2Status = Ec2StatusRepo().find_by_id(ec2_instance['_id'])
        repo = Ec2OperationLogRepo()
        unfinished_cmd = repo.get_last_unfinished_cmd()
        if unfinished_cmd is not None:
            unfinished_cmd: Ec2OperationLog
            cmd = unfinished_cmd['command']
            if cmd == 'start':
                return MessageGenerator().same_cmd_is_running(cmd, unfinished_cmd['started_at']).generate()
            return MessageGenerator().last_cmd_still_running(cmd, unfinished_cmd['started_at'], status['status']).generate()
        if status['status'] != 'stopped':
            return MessageGenerator().invalid_status_for_cmd('start', 'stopped', status['status']).generate()
        ec2_log_id = repo.insert(ec2_instance['_id'], 'start', self.user_id)
        try:
            current_status = await _ec2_start(
                ec2_instance['_id'], ec2_instance['aws_crediential_id'], ec2_log_id, self.user_id)
            return MessageGenerator().cmd_success('start', current_status).generate()
        except ClientError as e:
            repo.error_operation(ec2_log_id, e)
            return MessageGenerator().cmd_error('start', e)


class Ec2Stop(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) >= 2:
            raise InvalidCmd(
                MessageGenerator().invalid_cmd(
                    'ec2 alias', '<id | alias> or no input(The default Ec2 instance will be used)').generate())
        ec2_instance = _get_ec2_instance(None if len(cmds) == 0 else cmds[0])
        status: Ec2Status = Ec2StatusRepo().find_by_id(ec2_instance['_id'])
        repo = Ec2OperationLogRepo()
        unfinished_cmd = repo.get_last_unfinished_cmd()
        if unfinished_cmd is not None:
            unfinished_cmd: Ec2OperationLog
            cmd = unfinished_cmd['command']
            if cmd == 'start':
                return MessageGenerator().same_cmd_is_running(cmd, unfinished_cmd['started_at']).generate()
            return MessageGenerator().last_cmd_still_running(cmd, unfinished_cmd['started_at'], status['status']).generate()
        if status['status'] != 'stopped':
            return MessageGenerator().invalid_status_for_cmd('start', 'stopped', status['status']).generate()
        ec2_log_id = repo.insert(ec2_instance['_id'], 'start', self.user_id)
        try:
            current_status = await _ec2_start(
                ec2_instance['_id'], ec2_instance['aws_crediential_id'], ec2_log_id, self.user_id)
            return MessageGenerator().cmd_success('start', current_status).generate()
        except ClientError as e:
            repo.error_operation(ec2_log_id, e)
            return MessageGenerator().cmd_error('start', e)


class Ec2Alias(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) != 2:
            raise InvalidCmd(
                'ec2 alias: invalid input, expect <id | alias > <new alias>')
        identifier, newAlias = cmds
        repo = Ec2InstanceRepo()
        ins: Ec2Instance = repo.find_by_vague_id(identifier)
        if ins is None:
            return 'No such instance'
        success = repo.update_alias(
            ins['_id'], self.params['user_id'], newAlias)
        if success:
            return 'Success'
        return f'Alias: {newAlias} already existed'


class Ec2Cron(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 cron', cmds)
        return 'Not implemented'


class Ec2Handler(AsyncBaseMessageHandler):
    @property
    def bind(self):
        return Ec2Bind(self.params)

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
