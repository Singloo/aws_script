from src.logger import logger
from redis import asyncio as aioredis
import json
from src.types import CachedData

redis_conn = aioredis.Redis(
    host='redis',
    port=6379,
    db=0
)


class CacheKeys:
    def userdata(user_id: str):
        return f'userdata/{user_id}'

    def status_msg(instance_id: str):
        return f'statusmsg/{instance_id}'


async def save(key: str, data, exp: int | None = None):
    await redis_conn.set(key, json.dumps(data), ex=exp)


async def get(key: str):
    res = await redis_conn.get(key)
    if res is None:
        return None
    return json.loads(res)
