from typing import Any


class NoSuchHandler(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class InvalidCammand(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Invalid cammand', *args)


class BaseMessageHandler():
    params: dict
    '''
        params: {
            user_id: str,
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
            input = cmds[1:] if len(cmds) > 1 else None
            return res(input)
        except TypeError:
            raise InvalidCammand

    def _fallback(self):
        raise NoSuchHandler


class AsyncBaseMessageHandler():
    params: dict
    '''
        params: {
            user_id: str,
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
            input = cmds[1:] if len(cmds) > 1 else None
            return await res(input)
        except TypeError:
            raise InvalidCammand

    async def _fallback(self, cmds: list[str]):
        raise NoSuchHandler
