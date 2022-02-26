from sanic import HTTPResponse, Request, Sanic
import os
import atexit
from sanic.response import json, text
from logger import logger
import receive
import reply
from verification import wechat_verification
from ec2Handler import ec2_action_handler, is_valid_cmd
from redisConn import get_userdata
from scheduler import schedule_to_shut_down_ec2, sched
import asyncio

reserved_instance_id = os.getenv('reserved_instance_id')
SCHEDULE_TO_STOP_EC2 = True
TIME_OUT_MSG = 'Sorry, operation didnt done on time, task is still running, please check it out later'
app = Sanic('wechat_service')


@atexit.register
def on_exit():
    sched.shutdown()


if SCHEDULE_TO_STOP_EC2:
    logger.info('[SCHEDULE] starting')
    sched.remove_all_jobs()
    sched.add_job(schedule_to_shut_down_ec2, trigger='cron',
                  args=(reserved_instance_id,), hour=22-8)
    sched.start()
    logger.info('[SCHEDULE] running')


async def _timeout(time: float = 2.3, resp=(False, TIME_OUT_MSG)):
    await asyncio.sleep(time)
    logger.warn('timeout timeout timeout')
    return resp


async def asyncRace(*fs):
    loop = asyncio.get_event_loop()
    tasks = [loop.create_task(f) for f in fs]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    return [o.result() for o in done]


async def message_handler(msg, user_id, data=None):
    valid, tokens = is_valid_cmd(msg, data)
    if valid:
        task_done_res = await asyncRace(
            _timeout(), ec2_action_handler(tokens, user_id))
        logger.info(f'[{user_id}] async race result got: {task_done_res}')
        if len(task_done_res) == 1:
            return task_done_res[0][1]
        return [o[1] for o in task_done_res if o[1] != TIME_OUT_MSG][0]
    return 'We dont have service ready for you'


@app.post('/wx')
async def main_post(request: Request) -> HTTPResponse:
    recMsg = receive.parse_xml(request.body)
    cached_data = get_userdata(recMsg.FromUserName)
    logger.info(f'[user cached data] {cached_data}')
    logger.info(
        f'[content] {recMsg.Content}, [user] {recMsg.FromUserName} [msgId] {recMsg.MsgId} [type] {recMsg.MsgType}')
    if isinstance(recMsg, receive.Msg) and recMsg.MsgType == 'text':
        toUser = recMsg.FromUserName
        fromUser = recMsg.ToUserName
        content = await message_handler(
            recMsg.Content, recMsg.FromUserName, cached_data)
        replyMsg = reply.TextMsg(toUser, fromUser, content)
        return text(replyMsg.send())
    else:
        return text('success')


@app.get('/wx')
async def main_get(request):
    resp = wechat_verification(request.args)
    if resp is None:
        return text('nah')
    return text(resp)
