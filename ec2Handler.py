import re
import boto3
from logger import logger
import os
from botocore.exceptions import ClientError
import time
from redisConn import cache_userdata, cache_status_msg, get_status_msg
import asyncio

region_name = os.getenv('region_name')
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')

ss_str = os.getenv('ss_str')
ss_port = os.getenv('ss_port')

ec2 = boto3.resource('ec2',
                     region_name=region_name,
                     aws_access_key_id=aws_access_key_id,
                     aws_secret_access_key=aws_secret_access_key
                     )


def destruct_msg(msg):
    return msg.strip().split(' ')


def get_ec2_instance(instance_id):
    filtered = ec2.instances.filter(
        InstanceIds=[instance_id]
    )
    ins = list(filtered.all())[0]
    return ins


def is_valid_cmd(msg, data=None):
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


def start_ec2(instance_id):
    ins = get_ec2_instance(instance_id)
    if ins.state['Name'] != 'stopped':
        logger.info(f'[Instance is {ins.state["Name"]}]')
        return False, f"Instance current state is {ins.state['Name']}"
    response = ins.start()
    logger.info('[Instance successfully started]')
    return True, response['StartingInstances'][0]['CurrentState']['Name']


def stop_ec2(instance_id):
    ins = get_ec2_instance(instance_id)
    if ins.state['Name'] != 'running':
        logger.info(f'i[nstance is] {ins.state["Name"]}')
        return False, f"Instance current state is {ins.state['Name']}"
    response = ins.stop()
    logger.info('[Instance successfully stopped]')
    return True, response['StoppingInstances'][0]['CurrentState']['Name']


def compose_ss_token(ip,):
    return {
        'new_ss_token': f"{ss_str}{ip}:{ss_port}",
        'ip': ip
    }


def wait_for_ip(ins):
    ins.load()
    ip = ins.public_ip_address
    state = ins.state['Name']
    while ip is None:
        time.sleep(0.2)
        ins.load()
        ip = ins.public_ip_address
        state = ins.state['Name']
    return {'state': state, **compose_ss_token(ip)}


async def _get_and_set_ec2_status(instance_id):
    ins = get_ec2_instance(instance_id)
    addon = wait_for_ip(ins) if ins.state['Name'] != 'stopped' else {
        'state': 'stopped'}
    msg = '\n \n'.join(addon.values())
    cache_status_msg(instance_id, msg)
    logger.info(f'[{instance_id}] status msg cached')
    return msg


async def query_ec2_status(instance_id):
    msg = get_status_msg(instance_id)
    if msg is None:
        msg = await _get_and_set_ec2_status(instance_id)
        return True, msg
    else:
        logger.info(f'[{instance_id}] got cached status msg')
        loop = asyncio.get_event_loop()
        task = loop.create_task(_get_and_set_ec2_status(instance_id))
        task.add_done_callback(
            lambda *args: logger.info(f'[{instance_id}]: background task done'))
        return True, msg


async def ec2_action_handler(tokens, user_id):
    cmd = tokens[2]
    instance_id = tokens[1]
    try:
        if cmd in ['start']:
            success, resp = start_ec2(instance_id)
        if cmd in ['stop']:
            success, resp = stop_ec2(instance_id)
        if cmd in ['state', 'status']:
            success, resp = await query_ec2_status(instance_id)

        cache_userdata(user_id, {'instance_id': instance_id})
        logger.info(f'[Cache data saved] {user_id}')
        return success, resp

    except ClientError as e:
        logger.error(e)
        return False, 'An aws error encountered'
