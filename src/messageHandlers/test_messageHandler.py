from . import BaseMessageHandler, NoSuchHandler
import unittest


class Ec2Start(BaseMessageHandler):
    def __call__(self, cmds: list[str]):
        print('ec2 start', cmds)
        return 'start ' + cmds[0]


class Ec2Cron(BaseMessageHandler):
    def __call__(self, cmds: list[str]):
        print('ec2 cron', cmds)
        return 'cron'


class Ec2Handler(BaseMessageHandler):
    @property
    def start(self):
        return Ec2Start(self.params)

    @property
    def cron(self):
        return Ec2Cron(self.params)


class AwsList(BaseMessageHandler):
    def __call__(self, cmds: list[str]):
        print('[27 list]', cmds)
        return 'list'


class AwsRm(BaseMessageHandler):
    def __call__(self, cmds: list[str]):
        print('rm', cmds)
        return 'rm'


class AwsHandler(BaseMessageHandler):
    @property
    def list(self):
        return AwsList(self.params)

    @property
    def rm(self):
        return AwsRm(self.params)


class InputMapperEntry(BaseMessageHandler):
    @property
    def aws(self):
        return AwsHandler(self.params)

    @property
    def ec2(self):
        return Ec2Handler(self.params)


class TestMessageHandler(unittest.TestCase):
    def test_should_find_handler(self):
        cmd1 = ['aws', 'list']
        res1 = InputMapperEntry()(cmd1)
        self.assertEqual(res1, 'list')

    def test_should_return_param(self):
        cmd1 = ['ec2', 'start', 'someId']
        res1 = InputMapperEntry()(cmd1)
        self.assertEqual(res1, 'start someId')


if __name__ == '__main__':
    unittest.main()
