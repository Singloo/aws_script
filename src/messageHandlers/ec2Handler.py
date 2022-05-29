import math
import re
from src.logger import logger
from botocore.exceptions import ClientError
from src.db.redis import json_save, json_get, CacheKeys
from src.db.exceptions import ExceedMaximumNumber
import asyncio
from typing import List, TYPE_CHECKING, Tuple
from src.types import CachedData
import aioboto3
from src.utils.constants import REGION_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, SS_PORT, SS_STR
from . import AsyncBaseMessageHandler
from .InputValidator import ValidatorManager, Validator, SessionExpired, ValidatorInvalidAndExceedMaximumTimes, ValidatorInvalidInput, SessionFinished, NoSuchSession
from .exceptions import InvalidCmd
from src.db.awsCrediential import AwsCredientialRepo
from src.db.ec2Instance import Ec2InstanceRepo
from src.utils.util import re_strict_match
from functools import partial
import base64
from .helper import test_aws_resource

if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
else:
    EC2Client = object
    EC2ServiceResource = object
    Instance = object


def destruct_msg(msg: str):
    return msg.lower().strip().split(' ')


class Ec2InstanceManager():
    ec2: EC2ServiceResource

    def __init__(self, instance_id: str, region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> None:
        self.instance_id = instance_id
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    async def __aenter__(self, ):
        session = aioboto3.Session()
        self.ec2 = await session.resource('ec2',
                                          region_name=self.region_name,
                                          aws_access_key_id=self.aws_access_key_id,
                                          aws_secret_access_key=self.aws_secret_access_key).__aenter__()
        filtered = self.ec2.instances.filter(
            InstanceIds=[self.instance_id]
        )
        ins: Instance
        async for item in filtered.limit(1):
            ins = item
        return ins

    async def __aexit__(self, type, value, trace):
        await self.ec2.__aexit__(type, value, trace)


def getEc2Instance(instance_id: str):
    return Ec2InstanceManager(
        instance_id,
        REGION_NAME,
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY
    )


def is_valid_cmd(msg: str, data: CachedData | None = None) -> Tuple[bool, List[str]]:
    tokens = destruct_msg(msg)
    if msg in ['state', 'status', 'start', 'stop'] and data != None and data.get('instance_id') != None:
        logger.info('[reconstruct tokens with data]')
        tokens = ['ec2', data.get('instance_id'), tokens[0]]
    logger.info(f'[tokens] {tokens}')
    if len(tokens) != 3:
        return False, None
    flag = 0
    if tokens[0].lower() == 'ec2':
        flag += 1
        logger.info('[msg stage 1 pass]')
    if tokens[1] != None and re.fullmatch(r"^i-[a-z0-9]{17}$", tokens[1]) != None:
        flag += 1
        logger.info('[msg stage 2 pass]')
    if tokens[2] in ['start', 'state', 'stop', 'status']:
        flag += 1
        logger.info('[msg stage 3 pass]')
    return flag == 3, tokens


async def start_ec2(instance_id: str) -> Tuple[bool, str]:
    async with getEc2Instance(instance_id) as ins:
        ins_state = await ins.state
        ins_state = ins_state['Name']
        if ins_state != 'stopped':
            logger.info(f'[Instance is {ins_state}')
            return False, f"Instance current state is {ins_state}"
        response = await ins.start()
        logger.info('[Instance successfully started]')
        return True, response['StartingInstances'][0]['CurrentState']['Name']


async def stop_ec2(instance_id: str) -> Tuple[bool, str]:
    async with getEc2Instance(instance_id) as ins:
        ins_state = await ins.state
        ins_state = ins_state['Name']
        if ins_state != 'running':
            logger.info(f'[instance is] {ins_state}')
            return False, f"Instance current state is {ins_state}"
        response = await ins.stop()
        logger.info('[Instance successfully stopped]')
        return True, response['StoppingInstances'][0]['CurrentState']['Name']


def compose_ss_token(ip: str,):
    return {
        'new_ss_token': f"{SS_STR}{ip}:{SS_PORT}",
        'ip': ip
    }


async def load_ins(ins: Instance) -> Instance:
    '''
    Deprecated
    '''
    logger.info('[load_ins] start')
    await ins.load()
    logger.info('[load_ins] end')
    return ins


async def wait_for_ip(ins: Instance):
    logger.info('[wait_for_ip] start')
    ip = await ins.public_ip_address
    state = await ins.state
    loop_times = 1
    while ip is None:
        logger.info(f'[ip is none] wait for 0.2s')
        await asyncio.sleep(0.2)
        ip = await ins.public_ip_address
        state = await ins.state
        loop_times += 1
    logger.info(f'[wait_for_ip] end [times] {loop_times}')
    return {'state': state['Name'], **compose_ss_token(ip)}


async def _get_and_set_ec2_status(instance_id: str):
    logger.info('[_get_and_set_ec2_status] start')
    async with getEc2Instance(instance_id) as ins:
        ins_state = await ins.state
        ins_state = ins_state['Name']
        addon = await wait_for_ip(ins) if ins_state != 'stopped' else {
            'state': 'stopped'}
        msg = '\n \n'.join(addon.values())
        await json_save(CacheKeys.status_msg(instance_id), msg, exp=60*2)
        logger.info(f'[{instance_id}] status msg cached')
        logger.info('[_get_and_set_ec2_status] end')
        return msg


async def query_ec2_status(instance_id: str):
    msg = await json_get(CacheKeys.status_msg(instance_id))
    logger.info(f'[redis res] [cached msg] {instance_id}:{msg}')
    if msg is None:
        logger.info('[no cached msg] start to load ec2 ins')
        msg = await _get_and_set_ec2_status(instance_id)
        logger.info('[no cached msg] ec2 status loaded')
        return True, msg
    else:
        logger.info(f'[{instance_id}] got cached status msg')
        loop = asyncio.new_event_loop()
        task = loop.create_task(_get_and_set_ec2_status(instance_id))
        task.add_done_callback(
            lambda *args: logger.info(f'[{instance_id}]: background task done'))
        logger.info(f'return cached status msg')
        return True, msg


async def ec2_action_handler(tokens: List[str], user_id: str) -> Tuple[bool, str]:
    cmd = tokens[2]
    instance_id = tokens[1]
    try:
        if cmd in ['start']:
            success, resp = await start_ec2(instance_id)
        if cmd in ['stop']:
            success, resp = await stop_ec2(instance_id)
        if cmd in ['state', 'status']:
            success, resp = await query_ec2_status(instance_id)
        logger.info(f'[{user_id}] resp got')
        await json_save(CacheKeys.userdata(user_id), {'instance_id': instance_id}, exp=10*60)
        logger.info(f'[Cache data saved] {user_id}')
        return success, resp

    except ClientError as e:
        logger.error(e)
        return False, 'An aws error encountered'


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
        print('ec2 rm', cmds)


class Ec2Start(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 start', cmds)


class Ec2Status(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 status', cmds)


class Ec2Stop(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 stop', cmds)


class Ec2Alias(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 alias', cmds)


class Ec2Cron(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 cron', cmds)


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
        return Ec2Status(self.params)

    @property
    def state(self):
        return Ec2Status(self.params)

    @property
    def stop(self):
        return Ec2Stop(self.params)

    @property
    def alias(self):
        return Ec2Alias(self.params)

    @property
    def cron(self):
        return Ec2Cron(self.params)
