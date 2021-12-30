from sanic import Sanic
from sanic.response import json, text
from logger import logger
import receive
import reply
from verification import wechat_verification
from ec2Handler import ec2_action_handler, is_valid_cmd
from redisConn import get_userdata
app = Sanic('wechat_service')


def message_handler(msg, user_id, data=None):
    if is_valid_cmd(msg, data):
        success, resp = ec2_action_handler(msg, user_id)
        return resp
    return 'We dont have service ready for you'


@app.post('/wx')
async def main_post(request):
    # res = wechat_verification(request.args)
    # if res is None:
    #     return text('nah')
    logger.info(request.body)
    recMsg = receive.parse_xml(request.body)
    cached_data = get_userdata(recMsg.FromUserName)
    logger.info(f'user cached data {cached_data}')
    logger.info(
        f'content {recMsg.Content}, user {recMsg.FromUserName} msgId {recMsg.MsgId} type {recMsg.MsgType}')
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
