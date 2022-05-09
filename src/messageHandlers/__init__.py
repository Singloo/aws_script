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
            self.fallback()
        # is_child_instance = res.__base__ in self.__class__.__bases__
        # if is_child_instance:
        #     return res(self.params)(cmds[1:])
        return res(cmds[1:])
    def fallback(self):
        raise NoSuchHandler