import asyncio
from typing import TYPE_CHECKING, Coroutine, Callable
from bson.objectid import ObjectId
from .ec2InstanceManager import getEc2InstanceWithCredentialId
from .messageGenerator import MessageGenerator
from src.utils.util import async_race, timeout, re_strict_match
from src.utils.exceptions import TimeoutException
from src.db.ec2Status import Ec2StatusRepo
from src.db.ec2OperationLog import Ec2OperationLogRepo
from botocore.exceptions import ClientError
from src.types.type import Ec2Instance, Ec2OperationLog, Ec2Status
from src.db.ec2Instance import Ec2InstanceRepo
from functools import partial
import base64
from .exceptions import InvalidCmd
from src.logger.logger import logger
import re
from src.db.ec2CronLog import Ec2CronLogRepo

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


def update_log_and_instance_status(ec2_log_id: ObjectId, ec2_id: ObjectId, status: str, ip: str = None):
    '''
        update ec2 operaton log, and update status, ip of the instance
    '''
    Ec2OperationLogRepo().finish_operation(ec2_log_id)
    Ec2StatusRepo().update_status(ec2_id, status, ip)


def schedule_status_task(ec2_log_id: ObjectId, ec2_id: ObjectId, aws_crediential_id: ObjectId, expected_status: str | None = None):
    '''
        schedule a background job to query ec2 status.
    '''
    if expected_status is None:
        coro = load_and_get_status_once(ec2_id, aws_crediential_id)
    else:
        coro = get_status_until(
            ec2_id, aws_crediential_id, expected_status)
    loop = asyncio.get_event_loop()
    task = loop.create_task(coro)

    def _on_finish(_task: asyncio.Task):
        '''
            on get status finish, update Ec2OperationLog, Ec2Status
        '''
        status, ip = _task.result()[0]
        update_log_and_instance_status(ec2_log_id, ec2_id, status, ip)

    task.add_done_callback(_on_finish)


def create_and_schedule_status_task(ec2_id: ObjectId, aws_crediential_id: ObjectId, user_id: ObjectId, expected_status: str | None = None):
    '''
        create an operation log, and schedule a status task
    '''
    ec2_log_id = Ec2OperationLogRepo().insert(ec2_id, 'status', user_id)
    schedule_status_task(ec2_log_id, ec2_id,
                         aws_crediential_id, expected_status)


async def get_status_until(ec2_id: ObjectId, aws_crediential_id: ObjectId, expected_status: str):
    '''
        keep querying instance status, until it matches the provided expceted status.
        maximum times: 20
        wait 0.2s between each query
    '''
    max_times = 20
    wait_time = 0.2
    times = 0
    state, ip = None
    with getEc2InstanceWithCredentialId(ec2_id, aws_crediential_id) as ins:
        while state != expected_status or times < max_times:
            await asyncio.sleep(wait_time)
            state, ip = await load_and_get_ins_state_ip(ins)
            times += 1
        return state, ip


async def load_and_get_status_once(ec2_id: ObjectId, aws_crediential_id: ObjectId):
    '''
        load once, and return status, ip
    '''
    with getEc2InstanceWithCredentialId(ec2_id, aws_crediential_id) as ins:
        return load_and_get_ins_state_ip(ins)


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
                'ec2 start/stop/status', '<id | alias> or no input(The default Ec2 instance will be used)').generate())


def _get_ec2_instance(user_id: ObjectId, vague_id: str | None,) -> Ec2Instance:
    '''
        get default or specified ec2 instance
    '''
    if vague_id is None:
        return Ec2InstanceRepo().get_default()
    return Ec2InstanceRepo().find_by_vague_id(vague_id, user_id)


async def _ec2_start_or_stop(cmd: str, ec2_id: ObjectId, aws_crediential_id: ObjectId, ec2_log_id: ObjectId, user_id: ObjectId):
    '''
        start or stop
        1. start | stop
        2. get current state
        3. update log and instance state
        4. schedule a status task
    '''

    is_start_cmd = cmd == 'start'
    async with getEc2InstanceWithCredentialId(ec2_id, aws_crediential_id) as ins:
        try:
            # ins_state = await ins.state
            # prev_state = ins_state['Name']
            response = await ins.start() if is_start_cmd else await ins.stop()
            logger.info(f'[Instance successfully {cmd}ed]')
            resp_attr = 'StartingInstances' if is_start_cmd else 'StoppingInstances'
            curr_state: str = response[resp_attr][0]['CurrentState']['Name']
            update_log_and_instance_status(ec2_log_id, ec2_id, curr_state)
            expected_status = 'running' if is_start_cmd else 'stopped'
            create_and_schedule_status_task(
                ec2_id, aws_crediential_id, user_id, expected_status)
            return curr_state
        except Exception as e:
            Ec2OperationLogRepo().error_operation(ec2_log_id, e)
            logger.error(
                f'[ec2HandlerHelper 196] {cmd} ec2_id: {ec2_id} error: {e}')
            return MessageGenerator().cmd_error(cmd, e.args).generate()


ec2_start = partial(_ec2_start_or_stop, 'start')

ec2_stop = partial(_ec2_start_or_stop, 'stop')


async def ec2_status(ec2_id: ObjectId, aws_crediential_id: ObjectId, ec2_log_id: ObjectId, user_id: ObjectId):
    '''

    '''
    async with getEc2InstanceWithCredentialId(ec2_id, aws_crediential_id) as ins:
        try:
            ins_state, ip = await get_ins_state_and_ip(ins)
            update_log_and_instance_status(
                ec2_log_id, ec2_id, ins_state, ip)
            return ins_state
        except Exception as e:
            Ec2OperationLogRepo().error_operation(ec2_log_id, e)
            logger.error(
                f'[ec2 status error] ec2_id: {ec2_id} error: {e}')
            return MessageGenerator().cmd_error('status', e).generate()


def get_ec2_instance_status_and_unfinished_cmd(cmds: list[str], user_id: ObjectId):
    '''
        return ec2_instance, ec2_status, unfinished_cmd
    '''
    ec2_instance = _get_ec2_instance(
        user_id, None if len(cmds) == 0 else cmds[0])
    ec2_status: Ec2Status = Ec2StatusRepo().find_by_id(ec2_instance['_id'])
    repo = Ec2OperationLogRepo()
    unfinished_cmd = repo.get_last_unfinished_cmd(ec2_instance['_id'])
    return ec2_instance, ec2_status, unfinished_cmd


def handle_unfinished_cmd(unfinished_cmd: Ec2OperationLog, cmd_to_run: str, current_status: str):
    '''
        when user input a cmd, and there is an unfinished cmd,
    '''
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
        instance_operation: (ec2_id, aws_crediential_id, ec2_log_id, user_id) -> coroutine[str]

        1. check cmds
        2. get ec2_instance, ec2_status, unfinished_cmd
        3. check if has unfinished cmd
        4. if current status doesn't match expected status, return error
        5. insert operation log
        6. run command, race with 4s timeout
    '''
    assert_cmds_to_be_one(cmds)
    ec2_instance, ec2_status, unfinished_cmd = get_ec2_instance_status_and_unfinished_cmd(
        cmds, user_id)
    current_status = ec2_status['status']
    ec2_id, aws_crediential_id = ec2_instance['_id'], ec2_instance['aws_crediential_id']
    if unfinished_cmd is not None:
        return handle_unfinished_cmd(unfinished_cmd, cmd, current_status)
    if expected_status != None and current_status != expected_status:
        return MessageGenerator().invalid_status_for_cmd(cmd, expected_status, current_status).generate()
    ec2_log_id = Ec2OperationLogRepo().insert(
        ec2_id, cmd, user_id)
    try:
        coro = instance_operation(
            ec2_id, aws_crediential_id, ec2_log_id, user_id)
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


def cmd_executor_sync(cron_id: ObjectId, cmds: list[str], cmd: str, expected_status: str | None, user_id: ObjectId, instance_operation: Callable[[ObjectId, ObjectId, ObjectId, ObjectId], str]):
    '''
        synchroneous version of cmd_executor
    '''
    try:
        _id = Ec2CronLogRepo().insert(cron_id, cmd)
        coro = cmd_executor(cmds, cmd, expected_status,
                            user_id, instance_operation)
        res = asyncio.run(coro)
        Ec2CronLogRepo().finish(_id, res)
    except Exception as e:
        logger.error(f'[cmd_executor_sync error] {e}')
        Ec2CronLogRepo().error(_id, e)


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


def ec2_cron_validate_and_transform_params(cmds: list[str], user_id: ObjectId) -> tuple[Ec2Instance, tuple[int, int], str]:
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
        instance = Ec2InstanceRepo().find_by_vague_id(vague_id, user_id)
    if instance is None:
        raise InvalidCmd('ec2 cron: no such instance')
    cron_time = _ec2_cron_validate_cron_string(cron_string)
    _cmd = _ec2_cron_validate_cmd(cmd)
    return instance, cron_time, _cmd
