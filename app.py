from sanic import HTTPResponse, Request, Sanic
import atexit
from sanic.response import json, text, stream, ResponseStream
from src.logger import logger
import src.messageHandlers.receive as receive
import src.messageHandlers.reply as reply
from src.messageHandlers.verification import wechat_verification
from src.messageHandlers.ec2Handler import ec2_action_handler, is_valid_cmd
from src.db.redis import json_get, CacheKeys
from src.schedulers import schedule_to_shut_down_ec2, sched
from src.utils.util import async_race, timeout, TIME_OUT_MSG
from src.types import CachedData
from src.utils.constants import RESERVED_INSTANCE_ID, SENTRY_DSN
import sentry_sdk
from sentry_sdk.integrations.sanic import SanicIntegration
from src.db.user import UserRepo
sentry_sdk.init(
    SENTRY_DSN,

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
    integrations=[SanicIntegration()]
)

SCHEDULE_TO_STOP_EC2 = True

app = Sanic('wechat_service')


@atexit.register
def on_exit():
    sched.shutdown()


if SCHEDULE_TO_STOP_EC2:
    logger.info('[SCHEDULE] starting')
    sched.remove_all_jobs()
    sched.add_job(schedule_to_shut_down_ec2, trigger='cron',
                  args=(RESERVED_INSTANCE_ID,), hour=22-8, minute=0)
    sched.start()
    logger.info('[SCHEDULE] running')


async def message_handler(msg: str, user_id: str, data: CachedData | None = None):
    valid, tokens = is_valid_cmd(msg, data)
    if valid:
        task_done_res = await async_race(
            timeout(4), ec2_action_handler(tokens, user_id))
        logger.info(f'[{user_id}] async race result got: {task_done_res}')
        if len(task_done_res) == 1:
            return task_done_res[0][1]
        return [o[1] for o in task_done_res if o[1] != TIME_OUT_MSG][0]
    return 'We dont have service ready for you'


@app.post('/wx')
async def main_post(request: Request) -> HTTPResponse:
    recMsg = receive.parse_xml(request.body)
    cached_data = await json_get(CacheKeys.userdata(recMsg.FromUserName))
    logger.info(f'[user cached data] {cached_data}')
    logger.info(
        f'[content] {recMsg.Content}, [user] {recMsg.FromUserName} [msgId] {recMsg.MsgId} [type] {recMsg.MsgType}')
    if isinstance(recMsg, receive.Msg) and recMsg.MsgType == 'text':
        toUser = recMsg.FromUserName
        fromUser = recMsg.ToUserName
        userRepo = UserRepo()
        userId = userRepo.find_by_wechat_id(toUser)
        content = await message_handler(
            recMsg.Content, recMsg.FromUserName, cached_data)
        logger.info(f'[{recMsg.FromUserName}] reply ready')
        replyMsg = reply.TextMsg(toUser, fromUser, content)
        await request.respond(text(replyMsg.send()))
    else:
        return text('success')


@app.get('/wx')
async def main_get(request: Request) -> HTTPResponse:
    resp = wechat_verification(request.args)
    if resp is None:
        return text('nah')
    return text(resp)
