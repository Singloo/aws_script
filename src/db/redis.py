from functools import partial
from src.logger import logger
from redis import asyncio as aioredis
import json
from src.types import CachedData
from typing import Any, Callable
import pickle

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


class Serializer():
    @staticmethod
    def dumps(data: Any) -> str:
        raise NotImplementedError()

    @staticmethod
    def loads(data: str) -> Any:
        raise NotImplementedError()


class JsonSerializer(Serializer):
    @staticmethod
    def dumps(data: Any) -> str:
        return json.dumps(data)

    @staticmethod
    def loads(data: str) -> Any:
        return json.loads(data)


class PicklSerializer(Serializer):
    @staticmethod
    def dumps(data: Any) -> str:
        return pickle.dumps(data).decode('utf-8')

    @staticmethod
    def loads(data: str) -> Any:
        return pickle.loads(str.encode('utf-8'))


async def save(key: str, data: Any, serializer: Serializer,  exp: int | None = None,):
    await redis_conn.set(key, serializer.dumps(data), ex=exp)


async def get(key: str, serializer: Serializer):
    res = await redis_conn.get(key)
    if res is None:
        return None
    return serializer.loads(res)

json_save: Callable[[str, Any, int | None], None] = partial(
    save, serializer=JsonSerializer)
json_get: Callable[[str], Any | None] = partial(get, serializer=JsonSerializer)

pickle_save: Callable[[str, Any, int | None], None] = partial(
    save, serializer=PicklSerializer)
pickle_get: Callable[[str], Any | None] = partial(
    get, serializer=PicklSerializer)
