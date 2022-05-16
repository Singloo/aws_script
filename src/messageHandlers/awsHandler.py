from . import AsyncBaseMessageHandler
from .InputValidator import ValidatorManager, Validator


class AwsBind(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('bind')


class AwsList(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('list', cmds)


class AwsRm(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        print('rm', cmds)


class AwsHandler(AsyncBaseMessageHandler):
    @property
    def bind(self):
        return AwsBind(self.params)

    @property
    def list(self):
        return AwsList(self.params)

    @property
    def rm(self):
        return AwsRm(self.params)


regions = ["ap", "us", "ca", "eu", "me", "af", "sa", "cn"]

orientations = ['north', 'west', 'east', 'south',
                'southeast', 'southwest', 'northeast', 'northwest']

region_nums = ['1', '2', '3', '4']

region_regex_str = f"^({'|'.join(regions)})-({'|'.join(orientations)})-({'|'.join(region_nums)})$"

AWS_VALIDATORS: list[Validator] = [
    Validator(
        prompt='aws key id',
        invalid_prompt='aws key id is wrong',
        attribute_name='aws_key_id',
        validator=partial(re_strict_match, pattern='^[A-Z0-9]{20}$'),
        encrypt=True
    ),
    Validator(
        prompt='aws secret access key',
        invalid_prompt='aws secret access key is wrong',
        attribute_name='aws_secret_access_key',
        validator=partial(re_test, pattern='^[a-zA-Z0-9]{40}$'),
        encrypt=True
    ),
    Validator(
        prompt='region name',
        invalid_prompt='region name is invalid',
        attribute_name='region_name',
        validator=partial(re_strict_match, pattern=region_regex_str)
    ),
]
