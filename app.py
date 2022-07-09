from sanic import HTTPResponse, Request, Sanic
import atexit
from sanic.response import text, stream, ResponseStream
from src.logger import logger
import src.messageHandlers.receive as receive
import src.messageHandlers.reply as reply
from src.messageHandlers.verification import wechat_verification
from src.messageHandlers.InputMapper import InputMapperEntry
from src.schedulers import sched
from src.utils.constants import SENTRY_DSN
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


app = Sanic('wechat_service')
sched.start()


@atexit.register
def on_exit():
    sched.shutdown()


@app.post('/wx')
async def main_post(request: Request) -> HTTPResponse:
    recMsg = receive.parse_xml(request.body)
    logger.info(
        f'[content] {recMsg.Content}, [user] {recMsg.FromUserName} [msgId] {recMsg.MsgId} [type] {recMsg.MsgType}')
    if isinstance(recMsg, receive.Msg) and recMsg.MsgType == 'text':
        toUser = recMsg.FromUserName
        fromUser = recMsg.ToUserName
        userRepo = UserRepo()
        user_id = userRepo.find_by_wechat_id(toUser)
        normalized_msg = recMsg.Content.lower().strip().replace('_', '').split(' ')
        content = await InputMapperEntry(params={
            'user_id': user_id,
            'origin_input': recMsg.Content
        })(normalized_msg)
        logger.info(f'[app.py 48] [{recMsg.FromUserName}] {content}')
        replyMsg = reply.TextMsg(toUser, fromUser, content)
        await request.respond(text(replyMsg.send()))
    else:
        return text('success')


@ app.get('/wx')
async def main_get(request: Request) -> HTTPResponse:
    resp = wechat_verification(request.args)
    if resp is None:
        return text('nah')
    return text(resp)
