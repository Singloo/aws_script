from sanic import Sanic
from sanic.response import json, text
from logger import logger
import receive
import reply
from verification import wechat_verification
from ec2Handler import ec2_action_handler, is_valid_cmd
app = Sanic('wechat_service')


def message_handler(msg):
    logger.info(f'Msg content {msg}')
    if is_valid_cmd(msg):
        success, resp = ec2_action_handler(msg)
        return resp
    return 'We dont have service ready for you'


@app.post('/wx')
async def main_post(request):
    # res = wechat_verification(request.args)
    # if res is None:
    #     return text('nah')
    logger.info(request.body)
    recMsg = receive.parse_xml(request.body)
    if isinstance(recMsg, receive.Msg) and recMsg.MsgType == 'text':
        toUser = recMsg.FromUserName
        fromUser = recMsg.ToUserName
        content = message_handler(recMsg.Content)
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
