import asyncio
from typing import Any, TypeVar, Callable
from src.logger import logger
import re
from re import Pattern
TIME_OUT_MSG = "Sorry, operation didn't finish on time, task is still running, please check it out later"


async def timeout(time: float = 2.3, resp=(False, TIME_OUT_MSG)):
    await asyncio.sleep(time)
    return resp


async def async_race(*fs):
    loop = asyncio.get_event_loop()
    tasks = [loop.create_task(f) for f in fs]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    return [o.result() for o in done]

T = TypeVar('T')


def list_every(list: list[T], handler: Callable[[T], bool]) -> bool:
    '''
        same as js array.every
    '''
    res = True
    for item in list:
        if handler(item) == False:
            res = False
            break
    return res


def list_reduce(list: list[T], handler: Callable[[Any, Any], bool], initial_value: Any = None) -> Any:
    temp_value = initial_value
    for item in list:
        temp_value = handler(temp_value, item)
    return temp_value


def re_strict_match(string: str, pattern: Pattern[str],):
    res = re.search(pattern, string)
    return res != None and res.group(0) == string


def re_test(string: str, pattern: Pattern[str],):
    res = re.search(pattern, string)
    return res != None
