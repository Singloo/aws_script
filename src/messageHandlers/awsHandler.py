from . import AsyncBaseMessageHandler
from .InputValidator import ValidatorManager, Validator
from functools import partial
from src.utils.util import re_strict_match, re_test
from src.db.redis import CacheKeys


class AwsBind(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        uniq_key = CacheKeys.aws_validator_key(self.params.get('user_id'))
        vm: ValidatorManager = ValidatorManager.init_db_input_validator(
            AWS_VALIDATORS, uniq_key, 'awsCrediential')
        return vm.next()


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
        prompt='''You are going to bind aws crediential, please finish it in 5 min\nPlease input <aws key id>''',
        invalid_prompt='aws key id is wrong',
        attribute_name='aws_key_id',
        validator=partial(re_strict_match, pattern='^[A-Z0-9]{20}$'),
        encrypt=True
    ),
    Validator(
        prompt='Please input <aws secret access key>',
        invalid_prompt='aws secret access key is wrong',
        attribute_name='aws_secret_access_key',
        validator=partial(re_test, pattern='^[a-zA-Z0-9]{40}$'),
        encrypt=True
    ),
    Validator(
        prompt='Please input <region name>',
        invalid_prompt='region name is invalid',
        attribute_name='region_name',
        validator=partial(re_strict_match, pattern=region_regex_str)
    ),
]
