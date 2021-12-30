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
    if isinstance(res, str):
        return json.loads(res)
    return None
