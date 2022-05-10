from typing import Any


class NoSuchHandler(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class BaseMessageHandler():
    def __init__(self,params:Any = {}) -> None:
        self.params = params

    def __call__(self, cmds: list[str]):
        first = cmds[0] 
        res = getattr(self, first, None)
        if res is None:
            return self.fallback()
        return res(cmds[1:])

    def fallback(self):
        raise NoSuchHandler

class AsyncBaseMessageHandler():
    def __init__(self,params:Any = {}) -> None:
        self.params = params

    async def __call__(self, cmds: list[str]):
        first = cmds[0] 
        res = getattr(self, first, None)
        if res is None:
            return await self.fallback()
        return await res(cmds[1:])
        
    async def fallback(self):
        raise NoSuchHandler