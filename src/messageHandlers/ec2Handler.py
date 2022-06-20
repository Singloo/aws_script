import re
from src.logger import logger
from botocore.exceptions import ClientError
from src.db.redis import json_save, json_get, CacheKeys
from src.db.exceptions import ExceedMaximumNumber, NoSuchDocument
import asyncio
from typing import Callable, TYPE_CHECKING
from src.types.type import Ec2Instance, Ec2OperationLog, Ec2Status
from . import AsyncBaseMessageHandler
from .InputValidator import ValidatorManager, Validator, SessionExpired, ValidatorInvalidAndExceedMaximumTimes, ValidatorInvalidInput, SessionFinished, NoSuchSession
from .exceptions import InvalidCmd
from src.db.awsCrediential import AwsCredientialRepo
from src.db.ec2Instance import Ec2InstanceRepo
from src.db.ec2CronJob import Ec2CronRepo
from src.utils.util import re_strict_match
from src.db.ec2OperationLog import Ec2OperationLogRepo
from src.db.ec2Status import Ec2StatusRepo
from functools import partial
import base64
from .helper import test_aws_resource
from .messageGenerator import MessageGenerator
from bson.objectid import ObjectId
from src.utils.util import async_race, timeout
from src.utils.exceptions import TimeoutException
from .ec2HandlerHelper import get_ins_state_and_ip, update_log_and_instance_status, create_and_schedule_status_task
from .ec2InstanceManager import getEc2InstanceWithCredentialId


if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
    from mypy_boto3_ec2.type_defs import StartInstancesResultTypeDef, StopInstancesResultTypeDef
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


def assert_cmds_to_be_one(cmds: list[str]):
    '''
        for cmds ec2 start / ec2 stop / ec2 status
        expect one or zero input
    '''
    if len(cmds) >= 2:
        raise InvalidCmd(
            MessageGenerator().invalid_cmd(
                'ec2 status', '<id | alias> or no input(The default Ec2 instance will be used)').generate())


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


async def _ec2_start_or_stop(cmd: str, instance_id: ObjectId, aws_crediential_id: ObjectId, ec2_log_id: ObjectId, user_id: ObjectId):
    is_start_cmd = cmd == 'start'
    async with getEc2InstanceWithCredentialId(instance_id, aws_crediential_id) as ins:
        try:
            ins_state = await ins.state
            prev_state = ins_state['Name']
            response = await ins.start() if is_start_cmd else await ins.stop()
            logger.info(f'[Instance successfully {cmd}ed]')
            resp_attr = 'StartingInstances' if is_start_cmd else 'StoppingInstances'
            curr_state: str = response[resp_attr][0]['CurrentState']['Name']
            update_log_and_instance_status(ec2_log_id, instance_id, curr_state)
            expected_status = 'running' if is_start_cmd else 'stopped'
            create_and_schedule_status_task(
                instance_id, aws_crediential_id, user_id, expected_status)
            return curr_state
        except Exception as e:
            Ec2OperationLogRepo().error_operation(ec2_log_id, e)
            logger.error(
                f'[ec2 {cmd} error] instance_id: {instance_id} error: {e}')
            return MessageGenerator().cmd_error(cmd, e).generate()


_ec2_start = partial(_ec2_start_or_stop, 'start')

_ec2_stop = partial(_ec2_start_or_stop, 'stop')


async def _ec2_status(instance_id: ObjectId, aws_crediential_id: ObjectId, ec2_log_id: ObjectId, user_id: ObjectId):
    async with getEc2InstanceWithCredentialId(instance_id, aws_crediential_id) as ins:
        try:
            ins_state, ip = await get_ins_state_and_ip(ins)
            update_log_and_instance_status(
                ec2_log_id, instance_id, ins_state, ip)
            return ins_state
        except Exception as e:
            Ec2OperationLogRepo().error_operation(ec2_log_id, e)
            logger.error(
                f'[ec2 status error] instance_id: {instance_id} error: {e}')
            return MessageGenerator().cmd_error('status', e).generate()


def get_ec2_instance_status_and_unfinished_cmd(cmds: list[str]):
    ec2_instance = _get_ec2_instance(None if len(cmds) == 0 else cmds[0])
    ec2_status: Ec2Status = Ec2StatusRepo().find_by_id(ec2_instance['_id'])
    repo = Ec2OperationLogRepo()
    unfinished_cmd = repo.get_last_unfinished_cmd()
    return ec2_instance, ec2_status, unfinished_cmd


def handle_unfinished_cmd(unfinished_cmd: Ec2OperationLog, cmd_to_run: str, current_status: str):
    cmd = unfinished_cmd['command']
    if cmd == cmd_to_run:
        return MessageGenerator().same_cmd_is_running(cmd, unfinished_cmd['started_at']).generate()
    return MessageGenerator().last_cmd_still_running(cmd, unfinished_cmd['started_at'], current_status).generate()


def timeout_cmd_callback(cmd: str, ec2_log_id: ObjectId, task: asyncio.Task):
    '''
        callback for timeout command
    '''
    ec2_log: Ec2OperationLog = Ec2OperationLogRepo().find_by_id(ec2_log_id)
    logger.info(
        f'Command: {cmd} finished, task result: {task.result()}, time consumed: {(ec2_log["finished_at"] - ec2_log["started_at"]).seconds}')


async def cmd_executor(cmds: list[str], cmd: str, expected_status: str | None, user_id: ObjectId, instance_operation: Callable[[ObjectId, ObjectId, ObjectId, ObjectId], str]):
    '''
        execute command
        cmds: input params
        cmd: start | stop | status
        expected_status: stopped | running | None
        instance_operation: (instance_id, aws_crediential_id, ec2_log_id, user_id) -> coroutine[str]
    '''
    assert_cmds_to_be_one(cmds)
    ec2_instance, ec2_status, unfinished_cmd = get_ec2_instance_status_and_unfinished_cmd(
        cmds)
    current_status = ec2_status['status']
    instance_id, aws_crediential_id = ec2_instance['_id'], ec2_instance['aws_crediential_id']
    if unfinished_cmd is not None:
        return handle_unfinished_cmd(unfinished_cmd, cmd, current_status)
    if expected_status != None and current_status != expected_status:
        return MessageGenerator().invalid_status_for_cmd(cmd, expected_status, current_status).generate()
    ec2_log_id = Ec2OperationLogRepo().insert(
        instance_id, cmd, user_id)
    try:
        coro = instance_operation(
            instance_id, aws_crediential_id, ec2_log_id, user_id)
        current_status = await async_race(coro, timeout(4.0), cancel_pending=False, callback=partial(timeout_cmd_callback, cmd, ec2_log_id))
        res_msg = MessageGenerator().cmd_success(cmd, current_status)
        if cmd == 'status':
            res_msg.add_outline_token(
                ec2_instance['outline_token'], e).add_ip(ec2_status['ip'])
        return res_msg.generate()
    except TimeoutException:
        return MessageGenerator().cmd_timeout(cmd, current_status).add_outline_token(ec2_instance['outline_token'], e).add_ip(ec2_status['ip']).generate()
    except ClientError as e:
        Ec2OperationLogRepo().error_operation(ec2_log_id, e)
        return MessageGenerator().cmd_error(cmd, e).generate()


class Ec2Start(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return cmd_executor(cmds, 'start', 'stopped', self.user_id, _ec2_start)


class Ec2StatusCmd(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return cmd_executor(cmds, 'status', None, self.user_id, _ec2_status)


class Ec2Stop(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return cmd_executor(cmds, 'stop', 'running', self.user_id, _ec2_stop)


class Ec2Alias(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) > 2:
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


def _ec2_cron_validate_cron_string(cron_str: str):
    '''
        formate should be like 18:12
    '''
    try:
        hour, minute = cron_str.split(':')
        valid_hour = int(hour) <= 23 and int(hour) >= 0
        valid_minute = int(minute) <= 59 and int(minute) >= 0
        if valid_hour is False or valid_minute is False:
            raise InvalidCmd('ec2 cron: invalid cron string format')
        return int(hour), int(minute)
    except Exception as e:
        logger.info(f'[ec2 cron] invalid cron string {e}')
        raise InvalidCmd('ec2 cron: invalid cron string format')


def _ec2_cron_validate_cmd(cmd: str):
    '''
        command should be either start or stop
    '''
    if cmd.strip().lower() not in ['start', 'stop']:
        raise InvalidCmd(
            'ec2 cron: invalid command, should be "start" or "stop"')
    return cmd


def _ec2_cron_validate_and_transform_params(cmds: list[str]) -> tuple[Ec2Instance, tuple[int, int], str]:
    '''
        validate params and transform it
    '''
    if len(cmds) not in [2, 3]:
        raise InvalidCmd(
            'ec2 cron: invalid input, expect [id | alias ] <cron string> <command> \ncron string: hour:minute e.g 23:30 hour:[0:23], minute:[0:59]\n command: start | stop')
    if len(cmds) == 2:
        cron_string, cmd = cmds
        instance = Ec2InstanceRepo().get_default()
    else:
        vague_id, cron_string, cmd = cmds
        instance = Ec2InstanceRepo().find_by_vague_id(vague_id)
    if instance is None:
        raise InvalidCmd('ec2 cron: no such instance')
    cron_time = _ec2_cron_validate_cron_string(cron_string)
    _cmd = _ec2_cron_validate_cmd(cmd)
    return instance, cron_time, _cmd


class Ec2Cron(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) not in [2, 3]:
            raise InvalidCmd(
                'ec2 cron: invalid input, expect [id | alias ] <cron string> <command> \ncron string: hour:minute e.g 23:30 hour:[0:23], minute:[0:59]\n command: start | stop')
        instance, cron_time, _cmd = _ec2_cron_validate_and_transform_params(
            cmds)
        hour, minute = cron_time
        existed = Ec2CronRepo().find_by_time(
            instance['_id'], _cmd, hour, minute)
        if existed is not None:
            return MessageGenerator().existed('cron job')

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
