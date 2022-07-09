import asyncio
from typing import Any, TypeVar, Callable
from src.logger import logger
import re
from re import Pattern
from .exceptions import TimeoutException
import random
import string


async def timeout(time: float = 2.3):
    await asyncio.sleep(time)
    raise TimeoutException


async def async_race(*fs, cancel_pending=True, callback: Callable[[asyncio.Task], Any] | None = None):
    '''
        return [results], [pending coroutines]
    '''
    loop = asyncio.get_event_loop()
    tasks = [loop.create_task(f) for f in fs]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        if callback is not None:
            task.add_done_callback(callback)
            continue
        if cancel_pending:
            task.cancel()
    return [o.result() or o.exception() for o in done], pending

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


def list_reduce(list: list[T], handler: Callable[[Any, Any], Any], initial_value: Any = None) -> Any:
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


def desensitize_data(string: str, max_star_count: None | int = None, max_visvible_char: None | int = None):
    str_len = len(string)
    if str_len == 2:
        return string[0]+'*'
    visible_count = min(4, round(str_len * 0.3))
    if max_visvible_char != None and max_visvible_char < visible_count:
        visible_count = max_visvible_char

    star_count = str_len-visible_count*2
    if max_star_count != None and max_star_count < star_count:
        star_count = max_star_count
    stars = '*'*star_count
    return string[:visible_count] + stars + string[str_len-visible_count:]


def generate_alias(length: int = 2, n=10):
    assert n > 0, 'n must be greater than 0'
    return [''.join(random.choices(string.ascii_letters + string.digits, k=length)).lower() for _ in range(n)]
