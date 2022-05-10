from . import BaseMessageHandler


class AwsBind(BaseMessageHandler):
    def __call__(self, cmds: list[str]):
        print('bind')


class AwsList(BaseMessageHandler):
    def __call__(self, cmds: list[str]):
        print('list', cmds)


class AwsRm(BaseMessageHandler):
    def __call__(self, cmds: list[str]):
        print('rm', cmds)


class AwsHandler(BaseMessageHandler):
    bind = AwsBind

    list = AwsList

    rm = AwsRm
