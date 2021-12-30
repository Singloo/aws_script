import re
import boto3
from logger import logger
import os
from botocore.exceptions import ClientError
import time
from redisConn import cache_userdata, get_userdata

region_name = os.getenv('region_name')
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')

ss_str = os.getenv('ss_str')
ss_port = os.getenv('ss_port')


def destruct_msg(msg):
    return msg.strip().split(' ')


def get_ec2_instance(instance_id):
    ec2 = boto3.resource('ec2',
                         region_name=region_name,
                         aws_access_key_id=aws_access_key_id,
                         aws_secret_access_key=aws_secret_access_key
                         )
    filtered = ec2.instances.filter(
        InstanceIds=[instance_id]
    )
    ins = list(filtered.all())[0]
    return ins


def is_valid_cmd(msg, data=None):
    tokens = destruct_msg(msg)
    if msg in ['state', 'status', 'start', 'stop'] and data is not None and data.get('instance_id') is not None:
        tokens = ['ec2', data.get('instance_id'), tokens[0]]
    logger.info(f'[tokens] {tokens}')
    if len(tokens) != 3:
        return False
    flag = 0
    if tokens[0].lower() == 'ec2':
        flag += 1
        logger.info('[msg stage 1 pass]')
    if tokens[1] is not None and re.fullmatch(r"^i-[a-z0-9]{17}$", tokens[1]) is not None:
        flag += 1
        logger.info('[msg stage 2 pass]')
    if tokens[2] in ['start', 'state', 'stop', 'status']:
        flag += 1
        logger.info('[msg stage 3 pass]')
    return flag == 3, tokens


def start_ec2(instance_id):
    ins = get_ec2_instance(instance_id)
    if ins.state['Name'] == 'running':
        logger.info('[Instance is running]')
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


def query_ec2_status(instance_id):
    ins = get_ec2_instance(instance_id)
    addon = wait_for_ip(ins) if ins.state['Name'] != 'stopped' else {}
    msg = '\n'.join(addon.values())
    logger.info(f'[status got] {msg}')
    return True, msg


def ec2_action_handler(tokens, user_id):
    cmd = tokens[2]
    instance_id = tokens[1]
    try:
        if cmd in ['start']:
            success, resp = start_ec2(instance_id)
        if cmd in ['stop']:
            success, resp = stop_ec2(instance_id)
        if cmd in ['state', 'status']:
            success, resp = query_ec2_status(instance_id)
        cache_userdata(user_id, {'instance_id': instance_id})
        logger.info(f'[Cache data saved] {user_id}')
        return success, resp

    except ClientError as e:
        logger.error(e)
        return False, 'An aws error encountered'
