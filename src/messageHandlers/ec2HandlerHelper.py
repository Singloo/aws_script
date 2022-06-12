import asyncio
from typing import TYPE_CHECKING, Coroutine
from bson.objectid import ObjectId
from .ec2InstanceManager import getEc2InstanceWithCredentialId
from .messageGenerator import MessageGenerator
from src.utils.util import async_race, timeout
from src.utils.exceptions import TimeoutException
from src.db.ec2Status import Ec2StatusRepo
from src.db.ec2OperationLog import Ec2OperationLogRepo

if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
    from mypy_boto3_ec2.type_defs import StartInstancesResultTypeDef
else:
    EC2Client = object
    EC2ServiceResource = object
    Instance = object
    StartInstancesResultTypeDef = object


async def get_ins_state_and_ip(ins: Instance):
    '''
        return state and ip of the instance
    '''
    ip = await ins.public_ip_address
    state = await ins.state
    return state['Name'], ip


async def load_and_get_ins_state_ip(ins: Instance):
    await ins.load()
    return get_ins_state_and_ip(ins)


async def try_status_in_limited_time(get_status: Coroutine, seconds: float = 3.5):
    '''
        run get_statue coroutine in X seconds, raise TimeoutException if task didn't finish in time
    '''
    return async_race(get_status, timeout(seconds))


def update_log_and_instance_status(ec2_log_id: ObjectId, instance_id: ObjectId, status: str, ip: str = None):
    '''
        update ec2 operaton log, and update status, ip of the instance
    '''
    Ec2OperationLogRepo().finish_operation(ec2_log_id)
    Ec2StatusRepo().update_status(instance_id, status, ip)


def schedule_status_task(ec2_log_id: ObjectId, instance_id: ObjectId, aws_crediential_id: ObjectId, expected_status: str | None = None):
    '''
        schedule a background job to query ec2 status.
    '''
    if expected_status is None:
        coro = load_and_get_status_once(instance_id, aws_crediential_id)
    else:
        coro = get_status_until(
            instance_id, aws_crediential_id, expected_status)
    loop = asyncio.get_event_loop()
    task = loop.create_task(coro)

    def _on_finish(_task: asyncio.Task):
        '''
            on get status finish, update Ec2OperationLog, Ec2Status
        '''
        status, ip = _task.result()[0]
        update_log_and_instance_status(ec2_log_id, instance_id, status, ip)

    task.add_done_callback(_on_finish)


def create_and_schedule_status_task(instance_id: ObjectId, aws_crediential_id: ObjectId, user_id: ObjectId, expected_status: str | None = None):
    '''
        create an operation log, and schedule a status task
    '''
    ec2_log_id = Ec2OperationLogRepo().insert(instance_id, 'status', user_id)
    schedule_status_task(ec2_log_id, instance_id,
                         aws_crediential_id, expected_status)


async def get_status_until(instance_id: ObjectId, aws_crediential_id: ObjectId, expected_status: str):
    '''
        keep querying instance status, until it matches the provided expceted status.
        maximum times: 20
        wait 0.2s between each query
    '''
    max_times = 20
    wait_time = 0.2
    times = 0
    state, ip = None
    with getEc2InstanceWithCredentialId(instance_id, aws_crediential_id) as ins:
        while state != expected_status or times < max_times:
            await asyncio.sleep(wait_time)
            state, ip = await load_and_get_ins_state_ip(ins)
            times += 1
        return state, ip


async def load_and_get_status_once(instance_id: ObjectId, aws_crediential_id: ObjectId):
    '''
        load once, and return status, ip
    '''
    with getEc2InstanceWithCredentialId(instance_id, aws_crediential_id) as ins:
        return load_and_get_ins_state_ip(ins)
