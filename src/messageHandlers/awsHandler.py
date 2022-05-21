from . import AsyncBaseMessageHandler
from .InputValidator import ValidatorManager, Validator, SessionExpired, ValidatorInvalidAndExceedMaximumTimes, ValidatorInvalidInput, SessionFinished, NoSuchSession
from functools import partial
from src.utils.util import re_strict_match, re_test
import src.utils.crypto as Crypto
from src.db.redis import CacheKeys
import aioboto3
from botocore.exceptions import ClientError
from src.db.awsCrediential import AwsCredientialRepo
from src.db.exceptions import ExceedMaximumNumber
from src.types import AwsCrediential
from src.utils.util import desensitize_data
import src.utils.crypto as Crypto
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
else:
    EC2Client = object
    EC2ServiceResource = object
    Instance = object


class AwsBind(AsyncBaseMessageHandler):
    async def __call__(self, input: str | None = None):
        uniq_key = CacheKeys.aws_validator_key(self.params.get('user_id'))
        try:
            vm: ValidatorManager
            if input is None:
                vm = ValidatorManager.init_db_input_validator(
                    AWS_VALIDATORS, uniq_key, 'awsCrediential')
            else:
                vm = ValidatorManager.load_validator(uniq_key)
            return await vm.next(input)
        except SessionFinished:
            vm = ValidatorManager.load_validator(uniq_key)
            data = vm.collect()['data']
            col_name = vm.collect()['other_args']['col_name']
            res = await test_aws_crediential(
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

AWS_LIST_HEADER = '      [id]         [AWS access key id]        [Aws secret access key id]       [Region name]      [Alias]       [Created at]'

class AwsList(AsyncBaseMessageHandler):
    def __build_resp(self, instances: list[AwsCrediential]) -> str:
        def _single_ins(data: tuple[int, AwsCrediential]):
            idx, ins = data
            return f'{idx} {ins["_id"]} {desensitize_data(Crypto.decrypt(ins["aws_access_key_id"]), 4, 4)} {desensitize_data(Crypto.decrypt(ins["aws_secret_access_key"]), 5, 5)} {ins["region_name"]} {ins["alias"]} {ins["created_at"]}'
        return '\n'.join(map(_single_ins, enumerate(instances)))

    async def __call__(self, cmds: list[str]):
        user_id = self.params['user_id']
        inss = AwsCredientialRepo().find_all(user_id)
        if len(inss) == 0:
            return 'No result\nLets start by [aws bind]'
        return ''+self.__build_resp(inss)


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


async def test_aws_crediential(region_name: str, aws_access_key_id: str, aws_secret_access_key: str):
    try:
        session = aioboto3.Session()
        async with session.resource('ec2',
                                    region_name=region_name,
                                    aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key) as ec2:
            ec2: EC2ServiceResource
            all_instance = ec2.instances.all()
            async for item in all_instance.limit(1):
                pass
            return True
    except ClientError as e:
        return e.response['Error']['Message']
