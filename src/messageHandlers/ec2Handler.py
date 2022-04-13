import re
import boto3
from src.logger import logger
import os
from botocore.exceptions import ClientError
from src.db.redis import cache_userdata, cache_status_msg, get_status_msg
import asyncio
from typing import List, TYPE_CHECKING, Tuple
from src.types import CachedData
import aioboto3
from src.utils.constants import REGION_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, SS_PORT, SS_STR

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
        await cache_status_msg(instance_id, msg)
        logger.info(f'[{instance_id}] status msg cached')
        logger.info('[_get_and_set_ec2_status] end')
        return msg


async def query_ec2_status(instance_id: str):
    msg = await get_status_msg(instance_id)
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
        await cache_userdata(user_id, {'instance_id': instance_id})
        logger.info(f'[Cache data saved] {user_id}')
        return success, resp

    except ClientError as e:
        logger.error(e)
        return False, 'An aws error encountered'
