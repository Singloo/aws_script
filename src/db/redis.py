from functools import partial
from redis import asyncio as aioredis, Redis
import json
from typing import Any, Callable
import pickle


def get_redis() -> Redis:
    return aioredis.Redis(
        host='redis',
        port=6379,
        db=0,
        max_connections=20
    )


class CacheKeys:
    def userdata(user_id: str):
        return f'userdata/{user_id}'

    def aws_validator_key(user_id: str):
        return f'validator/{user_id}/aws'

    def ec2_validator_key(user_id: str):
        return f'validator/{user_id}/ec2'


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
    def dumps(data: Any) -> bytes:
        return pickle.dumps(data)

    @staticmethod
    def loads(data: bytes) -> Any:
        return pickle.loads(data)


async def save(key: str, data: Any, serializer: Serializer,  exp: int | None = None,):
    await get_redis().set(key, serializer.dumps(data), ex=exp)


async def get(key: str, serializer: Serializer):
    res = await get_redis().get(key)
    if res is None:
        return None
    return serializer.loads(res)


async def remove(*keys: list[str]):
    await get_redis().delete(*keys)

json_save: Callable[[str, Any, int | None], None] = partial(
    save, serializer=JsonSerializer)
json_get: Callable[[str], Any | None] = partial(get, serializer=JsonSerializer)

pickle_save: Callable[[str, Any, int | None], None] = partial(
    save, serializer=PicklSerializer)
pickle_get: Callable[[str], Any | None] = partial(
    get, serializer=PicklSerializer)
