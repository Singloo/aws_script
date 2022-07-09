from . import BaseMessageHandler, AsyncBaseMessageHandler
import unittest
from .exceptions import NoSuchHandler


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

# async


class AsyncEc2Start(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 start', cmds)
        return 'start ' + cmds[0]


class AsyncEc2Cron(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('ec2 cron', cmds)
        return 'cron'


class AsyncEc2Handler(AsyncBaseMessageHandler):
    @property
    def start(self):
        return AsyncEc2Start(self.params)

    @property
    def cron(self):
        return AsyncEc2Cron(self.params)


class AsyncAwsList(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('[84 list]', cmds)
        return 'list'


class AsyncAwsRm(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('rm', cmds)
        return 'rm'


class AsyncAwsHandler(AsyncBaseMessageHandler):
    @property
    def list(self):
        return AsyncAwsList(self.params)

    @property
    def rm(self):
        return AsyncAwsRm(self.params)


class AsyncInputMapperEntry(AsyncBaseMessageHandler):
    @property
    def aws(self):
        return AsyncAwsHandler(self.params)

    @property
    def ec2(self):
        return AsyncEc2Handler(self.params)


class TestMessageHandler(unittest.TestCase):
    def test_should_find_handler(self):
        cmd1 = ['aws', 'list']
        res1 = InputMapperEntry()(cmd1)
        self.assertEqual(res1, 'list')

    def test_should_return_param(self):
        cmd1 = ['ec2', 'start', 'someId']
        res1 = InputMapperEntry()(cmd1)
        self.assertEqual(res1, 'start someId')

    def test_should_raise_exception(self):
        with self.assertRaises(NoSuchHandler):
            cmd = ['ec2', 'cmd2']
            InputMapperEntry()(cmd)


class TestAsyncMessageHandler(unittest.IsolatedAsyncioTestCase):
    async def test_should_find_handler(self):
        cmd1 = ['aws', 'list']
        res1 = await AsyncInputMapperEntry()(cmd1)
        self.assertEqual(res1, 'list')

    async def test_should_return_param(self):
        cmd1 = ['ec2', 'start', 'someId']
        res1 = await AsyncInputMapperEntry()(cmd1)
        self.assertEqual(res1, 'start someId')

    async def test_should_raise_exception(self):
        with self.assertRaises(NoSuchHandler):
            cmd = ['ec2', 'cmd2']
            await AsyncInputMapperEntry()(cmd)


if __name__ == '__main__':
    unittest.main()
