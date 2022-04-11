import hashlib
from src.logger import logger

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
        return echostr
    else:
        return None
