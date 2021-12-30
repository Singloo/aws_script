from logger import logger
from redis import Redis
import json

redis_conn = Redis(
    host='redis',
    port=6379,
    db=0
)


def cache_userdata(user_id, data):
    redis_conn.set(user_id, json.dumps(data), ex=10*60)


def get_userdata(user_id):
    res = redis_conn.get(user_id)
    logger.info(f'[redis res] {user_id}:{res}')
    if res is None:
        return None
    return json.loads(res)
