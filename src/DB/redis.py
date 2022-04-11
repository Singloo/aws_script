from src.logger import logger
from redis import asyncio as aioredis
import json
from src.types import CachedData

redis_conn = aioredis.Redis(
    host='redis',
    port=6379,
    db=0
)


async def cache_userdata(user_id: str, data: CachedData):
    await redis_conn.set(user_id, json.dumps(data), ex=10*60)


async def get_userdata(user_id: str) -> CachedData:
    res = await redis_conn.get(user_id)
    if res is None:
        return None
    return json.loads(res)


async def cache_status_msg(instance_id: str, msg: str):
    await redis_conn.set(instance_id, json.dumps(msg), ex=60)


async def get_status_msg(instance_id: str) -> str:
    res = await redis_conn.get(instance_id)
    if res is None:
        return None
    return json.loads(res)
