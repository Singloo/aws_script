from sanic import Sanic
from sanic.response import json, text
import hashlib
from logger import logger
import receive
import reply

app = Sanic('wechat_service')


def wechat_verification(args):
    logger.info(args)
    signature = args.get('signature')
    timestamp = args.get('timestamp')
    nonce = args.get('nonce')
    echostr = args.get('echostr')
    token = 'timvel'
    arr = [token, timestamp, nonce]
    arr.sort()
    sha1 = hashlib.sha1()
    sha1.update(''.join(arr).encode())
    hashcode = sha1.hexdigest()
    logger.info(f'hashcode {hashcode}')
    logger.info(hashcode == signature)
    if hashcode == signature:
        return text(echostr)
    else:
        return None


@app.route('/wx',methods=['POST','OPTIONS'])
async def main_post(request):
    # res = wechat_verification(request.args)
    # if res is None:
    #     return text('nah')
    logger.info(request.body)
    recMsg = receive.parse_xml(request.body)
    if isinstance(recMsg, receive.Msg) and recMsg.MsgType == 'text':
        toUser = recMsg.FromUserName
        fromUser = recMsg.ToUserName
        content = "test"
        replyMsg = reply.TextMsg(toUser, fromUser, content)
        return text(replyMsg.send())
    else:
        return text('success')

@app.get('/wx')
async def main_get(request):
    return wechat_verification(request.args)


