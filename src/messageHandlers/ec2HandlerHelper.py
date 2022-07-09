import asyncio
from asyncio import CancelledError
from typing import TYPE_CHECKING, Callable
from bson.objectid import ObjectId

from src.db.awsCrediential import AwsCredientialRepo
from src.db.ec2CronJob import Ec2CronRepo
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
import traceback
from src.schedulers import sched
from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError

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
    return await get_ins_state_and_ip(ins)


# async def try_status_in_limited_time(get_status: Coroutine, seconds: float = 3.5):
#     '''
#         run get_statue coroutine in X seconds, raise TimeoutException if task didn't finish in time
#     '''
#     return async_race(get_status, timeout(seconds))


def update_log_and_instance_status(ec2_log_id: ObjectId, ec2_id: ObjectId, status: str, cmd: str, user_id: ObjectId, ip: str = None,):
    '''
        update ec2 operaton log, and update status, ip of the instance
    '''
    Ec2OperationLogRepo().finish_operation(ec2_log_id)
    Ec2StatusRepo().upsert_ec2_status(ec2_id, status, cmd, user_id, ip)


def _schedule_status_task(ec2_log_id: ObjectId, ec2_id: ObjectId, aws_crediential_id: ObjectId, user_id: ObjectId, expected_status: str | None = None, stop_event: asyncio.Event = None):
    '''
        schedule a background job to query ec2 status. require ec2_log_id
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
        try:
            logger.info(
                f'[schedule_status_task] schedule task got result {ec2_id}')
            status, ip = _task.result()
            update_log_and_instance_status(
                ec2_log_id, ec2_id, status, 'status', user_id, ip)
        except CancelledError:
            logger.info(
                f'[schedule_status_task] schedule status task, task cancelled {ec2_log_id}')
            Ec2OperationLogRepo().error_operation(ec2_log_id, 'CancelledError')
        finally:
            if stop_event != None:
                stop_event.set()
    logger.info(f'[schedule_status_task] scheduled status task {ec2_log_id}')
    task.add_done_callback(_on_finish)
    # if stop_event is not None:
    #     stop_event_task = loop.create_task(stop_event.wait())
    #     while(stop_event_task.done() is False):
    #         pass
    #     logger.info(f'[_schedule_status_task done]')


def create_and_schedule_status_task(ec2_id: ObjectId, aws_crediential_id: ObjectId, user_id: ObjectId, expected_status: str | None = None, stop_event: asyncio.Event = None):
    '''
        create an operation log, and schedule a status task
    '''
    logger.info(
        '[create_and_schedule_status_task] start')
    ec2_log_id = Ec2OperationLogRepo().insert(ec2_id, 'status', user_id)
    _schedule_status_task(ec2_log_id, ec2_id,
                          aws_crediential_id, user_id, expected_status, stop_event)


async def get_status_until(ec2_id: ObjectId, aws_crediential_id: ObjectId, expected_status: str):
    '''
        keep querying instance status, until it matches the provided expceted status.
        maximum times: 20
        wait 0.2s between each query
    '''
    max_times = 20
    wait_time = 0.2
    times = 0
    state = None
    ip = None
    async with getEc2InstanceWithCredentialId(ec2_id, aws_crediential_id) as ins:
        while state != expected_status or times < max_times:
            await asyncio.sleep(wait_time)
            state, ip = await load_and_get_ins_state_ip(ins)
            times += 1
        return state, ip


async def load_and_get_status_once(ec2_id: ObjectId, aws_crediential_id: ObjectId):
    '''
        load once, and return status, ip
    '''
    async with getEc2InstanceWithCredentialId(ec2_id, aws_crediential_id) as ins:
        return await load_and_get_ins_state_ip(ins)


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


def assert_cmds_length(cmds: list[str]):
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


async def _ec2_start_or_stop(cmd: str, ec2_id: ObjectId, aws_crediential_id: ObjectId, ec2_log_id: ObjectId, user_id: ObjectId, stop_event: asyncio.Event = None):
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
            if is_start_cmd:
                response = await ins.start()
                resp_attr = 'StartingInstances'
                expected_status = 'running'
            else:
                response = await ins.stop()
                resp_attr = 'StoppingInstances'
                expected_status = 'stopped'
            logger.info(f'[Instance successfully {cmd}ed]')
            curr_state: str = response[resp_attr][0]['CurrentState']['Name']
            update_log_and_instance_status(
                ec2_log_id, ec2_id, curr_state, cmd, user_id, None)
            create_and_schedule_status_task(
                ec2_id, aws_crediential_id, user_id, expected_status, stop_event)
            return curr_state
        except Exception as e:
            Ec2OperationLogRepo().error_operation(ec2_log_id, e)
            traceback.print_exc()
            logger.error(
                f'[ec2_start_or_stop] {cmd} ec2_id: {ec2_id} error: {e}')
            return MessageGenerator().cmd_error(cmd, e.args).generate()


ec2_start = partial(_ec2_start_or_stop, 'start')

ec2_stop = partial(_ec2_start_or_stop, 'stop')


async def ec2_status(ec2_id: ObjectId, aws_crediential_id: ObjectId, ec2_log_id: ObjectId, user_id: ObjectId, *args):
    '''
        get ec2 status
    '''
    async with getEc2InstanceWithCredentialId(ec2_id, aws_crediential_id) as ins:
        try:
            ins_state, ip = await get_ins_state_and_ip(ins)
            update_log_and_instance_status(
                ec2_log_id, ec2_id, ins_state, 'status', user_id, ip)
            return ins_state
        except Exception as e:
            Ec2OperationLogRepo().error_operation(ec2_log_id, e)
            logger.error(
                f'[ec2 status error] ec2_id: {ec2_id} error: {e}')
            return MessageGenerator().cmd_error('status', e).generate()


def init_ec2_status(ec2_id: ObjectId, aws_crediential_id: ObjectId, user_id: ObjectId):
    ec2_log_id = Ec2OperationLogRepo().insert(
        ec2_id, 'status', user_id)
    coro = ec2_status(ec2_id, aws_crediential_id, ec2_log_id, user_id)
    loop = asyncio.get_event_loop()
    task = loop.create_task(coro)
    task.add_done_callback(lambda x: logger.info(
        f'[init_ec2_status] finish initialization of ec2 status {ec2_id}'))


def get_ec2_instance_status_and_unfinished_cmd(cmds: list[str], user_id: ObjectId):
    '''
        return ec2_instance, ec2_status, unfinished_cmd
    '''
    ec2_instance = _get_ec2_instance(
        user_id, None if len(cmds) == 0 else cmds[0])
    ec2_status: Ec2Status = Ec2StatusRepo().find_by_ec2_id(ec2_instance['_id'])
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
        will update ec2 operation log status to `timeout`
    '''
    try:
        Ec2OperationLogRepo().timeout_finish_operation(ec2_log_id)
        ec2_log: Ec2OperationLog = Ec2OperationLogRepo().find_by_id(ec2_log_id)
        logger.info(
            f'[timeout_cmd_callback] Command: {cmd} finished, task result: {task.result()}, time consumed: {(ec2_log["finished_at"] - ec2_log["started_at"]).seconds}')
    except CancelledError:
        logger.info(f'[timeout_cmd_callback] task cancel error')


async def cmd_executor(cmds: list[str], cmd: str, expected_status: str | None, user_id: ObjectId, instance_operation: Callable[[ObjectId, ObjectId, ObjectId, ObjectId], str], stop_event: asyncio.Event = None):
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
    assert_cmds_length(cmds)
    # get ec2 instance, ec2 status, and unfinished command
    ec2_instance, ec2_status, unfinished_cmd = get_ec2_instance_status_and_unfinished_cmd(
        cmds, user_id)
    current_status = ec2_status['status']
    ec2_id, aws_crediential_id = ec2_instance['_id'], ec2_instance['aws_crediential_id']
    # if has unfinished cmd, return
    if unfinished_cmd is not None:
        return handle_unfinished_cmd(unfinished_cmd, cmd, current_status)
    # if has expected status, and doesn't match current status, return.
    # start and stop command will have a expected status
    if expected_status != None and current_status != expected_status:
        # status doesn't match, return msg and schedule a status task
        create_and_schedule_status_task(
            ec2_id, aws_crediential_id, user_id, stop_event)
        return MessageGenerator().invalid_status_for_cmd(cmd, expected_status, current_status).generate()
    ec2_log_id = Ec2OperationLogRepo().insert(
        ec2_id, cmd, user_id)
    try:
        coro = instance_operation(
            ec2_id, aws_crediential_id, ec2_log_id, user_id, stop_event)
        res, pending_coros = await async_race(coro, timeout(4.0), cancel_pending=False)
        current_status = res[0]
        if isinstance(current_status, TimeoutException):
            # timeout
            logger.info(f'[cmd_executor] timout exception')
            done_callback = partial(timeout_cmd_callback, cmd, ec2_log_id)
            for task in pending_coros:
                logger.info(f'[cmd_executor] task add callback')
                task.add_done_callback(done_callback)
            return MessageGenerator().cmd_timeout(cmd, current_status).add_outline_token(ec2_instance['outline_token'], e).add_ip(ec2_status['ip']).generate()
        # successfully got result
        # cancel timeout task
        for task in pending_coros:
            task.cancel()
        res_msg = MessageGenerator().cmd_success(cmd, current_status)
        outline_token = ec2_instance.get('outline_token', None)
        ip = ec2_status.get('ip', None)
        if cmd == 'status' and ip != None:
            if outline_token != None:
                res_msg.separator().add_outline_token(outline_token, ip)
            res_msg.separator().add_ip(ip)
        if stop_event is not None:
            logger.info(f'[cmd_executor] wait for stop event signal')
            await stop_event.wait()
            logger.info(f'[cmd_executor] stop event signal received')
        return res_msg.generate()
    except ClientError as e:
        Ec2OperationLogRepo().error_operation(ec2_log_id, e)
        return MessageGenerator().cmd_error(cmd, e).generate()


def cmd_executor_cron(cron_id: ObjectId, cmds: list[str], cmd: str, expected_status: str | None, user_id: ObjectId, instance_operation: Callable[[ObjectId, ObjectId, ObjectId, ObjectId], str]):
    '''
        synchroneous version of cmd_executor
    '''
    try:
        _id = Ec2CronLogRepo().insert(cron_id, cmd)
        stop_event = asyncio.Event()
        coro = cmd_executor(cmds, cmd, expected_status,
                            user_id, instance_operation, stop_event)
        res = asyncio.run(coro)
        logger.info(f'[cmd_executor_cron] task done')
        Ec2CronLogRepo().finish(_id, res)
    except Exception as e:
        traceback.print_exc()
        logger.error(f'[cmd_executor_cron] error {e}')
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


def ec2_cron_schedule_job(ec2_id: ObjectId, user_id: ObjectId, ec2_cron_id: ObjectId, cmd: str, hour: int, minute: int):
    '''
        schedule cron job
    '''
    CRON_PARAMS = {
        'start': ([ec2_id],  'start', 'stopped', user_id, ec2_start),
        'stop': ([ec2_id], 'stop', 'running', user_id, ec2_stop)
    }
    job: Job = sched.add_job(cmd_executor_cron, args=(
        ec2_cron_id, *CRON_PARAMS[cmd]), trigger='cron', hour=hour, minute=minute)
    return job


def rm_aws(aws_id: ObjectId):
    '''
        return 1, ec2 instance deleted count, ec2 cron deleted count
    '''
    AwsCredientialRepo().rm_by_id(aws_id)
    deleted_count = rm_ec2(None, aws_id)
    return 1, *deleted_count


def rm_ec2(ec2_id: ObjectId = None, aws_id: ObjectId = None):
    '''
        return ec2 instance deleted count, ec2 cron deleted count
    '''
    if int(bool(ec2_id)) + int(bool(aws_id)) != 1:
        return 0, 0
    ec2_deleted_count = 0
    ec2_cron_deleted_count = 0
    if ec2_id is not None:
        ec2_deleted_count = Ec2InstanceRepo().rm_by_id(ec2_id).modified_count
        ec2_ids = [ec2_id]
    if aws_id is not None:
        instances = Ec2InstanceRepo().find_by_aws_id(aws_id)
        ec2_deleted_count = Ec2InstanceRepo().rm_by_aws_crediential_id(aws_id)
        ec2_ids = [instance['_id'] for instance in instances]
    # try to delete schedules
    rm_cron_schedules(ec2_ids)
    # remove ec2 status
    removed_count = Ec2StatusRepo().rm_by_ec2_ids(ec2_ids)
    logger.info(f'[rm_ec2] removed [{removed_count}] ec2 status')
    # remove cron jobs from DB
    ec2_cron_deleted_count = Ec2CronRepo().rm_by_ec2_ids(ec2_ids)
    return ec2_deleted_count, ec2_cron_deleted_count


def rm_cron_schedules(ec2_ids: list[ObjectId]):
    cursor = Ec2CronRepo().find_by_ec2_ids(ec2_ids)
    for ins in cursor:
        try:
            sched.remove_job(ins['job_id'])
            logger.info(f'[rm_cron_schedules] job {ins["job_id"]} removed')
        except JobLookupError:
            logger.info(f'[rm_cron_schedules] job {ins["job_id"]} not found')
