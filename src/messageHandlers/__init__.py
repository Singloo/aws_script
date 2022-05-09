class NoSuchHandler(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class BaseMessageHandler():
    def __call__(self, cmds: list[str]):
        first = cmds[0]
        res = getattr(self, first, None)
        if res is None:
            raise NoSuchHandler
        return res(cmds[1:])