from asyncio.log import logger
from . import AsyncBaseMessageHandler
from .InputValidator import ValidatorManager, Validator, SessionExpired, ValidatorInvalidAndExceedMaximumTimes, ValidatorInvalidInput, SessionFinished, NoSuchSession
from functools import partial
from src.utils.util import re_strict_match, re_test
import src.utils.crypto as Crypto
from src.db.redis import CacheKeys
from src.db.awsCrediential import AwsCredientialRepo
from src.db.exceptions import ExceedMaximumNumber
from src.types import AwsCrediential
from src.utils.util import desensitize_data
from .exceptions import InvalidCmd
from .helper import test_aws_resource
from .messageGenerator import MessageGenerator


class AwsBind(AsyncBaseMessageHandler):
    async def __call__(self, input: str | None = None):
        uniq_key = CacheKeys.aws_validator_key(self.params.get('user_id'))
        try:
            vm: ValidatorManager
            if input is None:
                vm = ValidatorManager.init_db_input_validator(
                    AWS_VALIDATORS, uniq_key, 'awsCrediential')
            else:
                vm = await ValidatorManager.load_validator(uniq_key)
            return await vm.next(input)
        except SessionFinished:
            vm = await ValidatorManager.load_validator(uniq_key)
            data = vm.collect()['data']
            col_name = vm.collect()['other_args']['col_name']
            res = await test_aws_resource(
                data['region_name'], Crypto.decrypt(data['aws_access_key_id']), Crypto.decrypt(data['aws_secret_access_key']))
            if isinstance(res, str):
                return res
            object_id, alias = AwsCredientialRepo().insert(
                {**data, 'encrypted': True},
                self.params.get('user_id')
            )
            return f'Success, your credientials are encrypted well in our database.\n [ID]: {object_id} \n[Default Alias]:{alias}'
        except ValidatorInvalidAndExceedMaximumTimes:
            return 'Invalid input and exceed maximum retry times, please try again.'
        except ValidatorInvalidInput:
            return 'Invalid input'
        except SessionExpired:
            return 'Sorry, session is expired, please try again.'
        except NoSuchSession:
            return 'No aws bind session, please try again'
        except ExceedMaximumNumber:
            return 'Sorry, you cannot bind more AWS crediential(maximum 100)'


class AwsList(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        logger.info(f'[aws list]: {self.user_id}')
        user_id = self.user_id
        inss = AwsCredientialRepo().find_all(user_id)
        if len(inss) == 0:
            return 'No result\nLets start by [aws bind]'
        msgGen = MessageGenerator().list_header('Aws list', len(inss))
        for ins in inss:
            ins['aws_access_key_id'] = desensitize_data(
                ins["aws_access_key_id"], 4, 4)
            ins['aws_secret_access_key'] = desensitize_data(
                ins["aws_secret_access_key"], 5, 5)
            msgGen.list_item(ins)
        return msgGen.generate()


class AwsRm(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        if len(cmds) != 1:
            raise InvalidCmd('aws rm: invalid input, expect id or alias')
        identifier = cmds[0]
        repo = AwsCredientialRepo()
        ins = repo.find_by_vague_id(identifier)
        if ins is None:
            return 'No such instance'
        repo.delete_from_id(ins['_id'])
        return f'Success, instance: {identifier} has been removed.'


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
