from logger import logger
from redis import Redis
import json
from myType import CachedData

redis_conn = Redis(
    host='redis',
    port=6379,
    db=0
)


def cache_userdata(user_id: str, data: CachedData):
    redis_conn.set(user_id, json.dumps(data), ex=10*60)


def get_userdata(user_id: str) -> CachedData:
    res = redis_conn.get(user_id)
    if res is None:
        return None
    return json.loads(res)


def cache_status_msg(instance_id: str, msg: str):
    redis_conn.set(instance_id, json.dumps(msg), ex=60)


def get_status_msg(instance_id: str) -> str:
    res = redis_conn.get(instance_id)
    if res is None:
        return None
    return json.loads(res)
