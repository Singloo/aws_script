from sanic import Sanic
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

reserved_instance_id = os.getenv('reserved_instance_id')
SCHEDULE_TO_STOP_EC2 = True

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

def message_handler(msg, user_id, data=None):
    valid, tokens = is_valid_cmd(msg, data)
    if valid:
        success, resp = ec2_action_handler(tokens, user_id)
        return resp
    return 'We dont have service ready for you'


@app.post('/wx')
async def main_post(request):
    recMsg = receive.parse_xml(request.body)
    cached_data = get_userdata(recMsg.FromUserName)
    logger.info(f'[user cached data] {cached_data}')
    logger.info(
        f'[content] {recMsg.Content}, [user] {recMsg.FromUserName} [msgId] {recMsg.MsgId} [type] {recMsg.MsgType}')
    if isinstance(recMsg, receive.Msg) and recMsg.MsgType == 'text':
        toUser = recMsg.FromUserName
        fromUser = recMsg.ToUserName
        content = message_handler(
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


