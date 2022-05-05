from ast import pattern
import unittest
from InputValidator import ValidatorManager,Validator
from src.utils.util import re_strict_match,re_test
from functools import partial

regions = ["ap", "us", "ca", "eu", "me", "af", "sa", "cn"]

orientations = ['north', 'west', 'east', 'south',
                'southeast', 'southwest', 'northeast', 'northwest']

region_nums = ['1', '2', '3', '4']

region_regex_str = f"^({'|'.join(regions)})-({'|'.join(orientations)})-({'|'.join(region_nums)})$"

AWS_VALIDATORS:list[Validator] = [
    Validator(
        prompt='aws key id',
        invalid_prompt='aws key id is wrong',
        attribute_name='aws_key_id',
        validator= partial(re_strict_match, pattern='^[A-Z0-9]{20}$')
    ),
    Validator(
        prompt='aws secret access key',
        invalid_prompt='aws secret access key is wrong',
        attribute_name='aws_secret_access_key',
        validator=partial(re_test,pattern='^[a-zA-Z0-9]{40}$')
    ),
    Validator(
        prompt='region name',
        invalid_prompt='region name is invalid',
        attribute_name='region_name',
        validator=partial(re_strict_match,pattern=region_regex_str)
    ),
]

 
class TestAwsValidator(unittest.TestCase):
    def __init__(self) -> None:
        self.validator_manager = ValidatorManager.init_db_input_validator(
            AWS_VALIDATORS,
            'test_aws_validator',
            'aws'
        )
    