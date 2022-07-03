from typing import Any
from .exceptions import NoSuchHandler


class BaseMessageHandler():
    params: dict
    '''
        params: {
            user_id: ObjectId,
            origin_input: str,
            ...other params 
        }
    '''

    def __init__(self, params: Any = {}) -> None:
        self.params: dict = params

    def __call__(self, cmds: list[str]):
        try:
            first = cmds[0]
            res = getattr(self, first, None)
            if res is None:
                return self._fallback(cmds)
            input = cmds[1:]
            return res(input)
        except TypeError as e:
            raise TypeError(*e.args, cmds)

    def _fallback(self):
        raise NoSuchHandler


class AsyncBaseMessageHandler():
    params: dict
    '''
        params: {
            user_id: ObjectId,
            origin_input: str,
            ...other params 
        }
    '''

    def __init__(self, params: Any = {}) -> None:
        self.params: dict = params

    async def __call__(self, cmds: list[str]):
        try:
            first = cmds[0]
            res = getattr(self, first, None)
            if res is None:
                return await self._fallback(cmds)
            input = cmds[1:]
            return await res(input)
        except TypeError as e:
            raise TypeError(*e.args, cmds)

    async def _fallback(self, cmds: list[str]):
        raise NoSuchHandler

    @property
    def user_id(self):
        return self.params['user_id']
