import unittest
from .inputValidator import ValidatorManager, Validator, SessionFinished, SessionExpiredException
from src.utils.util import re_strict_match, re_test
from functools import partial
from src.utils.constants import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME

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


class TestAwsValidator(unittest.IsolatedAsyncioTestCase):
    validator_manager: ValidatorManager

    def setUp(self) -> None:
        self._init_validator()

    def _init_validator(self):
        self.validator_manager = ValidatorManager.init_db_input_validator(
            AWS_VALIDATORS,
            'test_aws_validator',
            'aws'
        )

    async def test_input_correct(self):
        prompt1 = await self.validator_manager.next()
        self.assertEqual(prompt1, AWS_VALIDATORS[0].prompt)
        prompt2 = await self.validator_manager.next(AWS_ACCESS_KEY_ID)
        self.assertEqual(prompt2, AWS_VALIDATORS[1].prompt)
        prompt3 = await self.validator_manager.next(AWS_SECRET_ACCESS_KEY)
        self.assertEqual(prompt3, AWS_VALIDATORS[2].prompt)
        with self.assertRaises(SessionFinished):
            await self.validator_manager.next(REGION_NAME)


if __name__ == '__main__':
    unittest.main()
