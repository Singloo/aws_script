import asyncio
from src.logger import logger
TIME_OUT_MSG = "Sorry, operation didn't finish on time, task is still running, please check it out later"


async def timeout(time: float = 2.3, resp=(False, TIME_OUT_MSG)):
    await asyncio.sleep(time)
    return resp


async def async_race(*fs):
    loop = asyncio.get_event_loop()
    tasks = [loop.create_task(f) for f in fs]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    return [o.result() for o in done]
