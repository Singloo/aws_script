import unittest
from .inputValidator import ValidatorManager, Validator, SessionFinished, SessionExpiredException, ValidatorInvalidInput
from src.utils.util import re_strict_match, re_test
from functools import partial
from src.utils.constants import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME
from src.db.redis import CacheKeys

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

    def setUp(self) -> None:
        pass

    def _init_validator(self, uniq_key: str):
        return ValidatorManager.init_db_input_validator(
            AWS_VALIDATORS,
            uniq_key,
            'aws'
        )

    async def test_input_correct(self):
        key = CacheKeys.aws_validator_key('test_input_correct')
        validator_manager = self._init_validator(key)
        prompt1 = await validator_manager.next()
        self.assertEqual(prompt1, AWS_VALIDATORS[0].prompt)
        print('test_input_correct step1 pass')

        validator_manager = await ValidatorManager.load_validator(key)
        print(f'[test 64] {validator_manager}')
        prompt2 = await validator_manager.next(AWS_ACCESS_KEY_ID)
        self.assertEqual(prompt2, AWS_VALIDATORS[1].prompt)
        print('test_input_correct step2 pass')

        validator_manager = await ValidatorManager.load_validator(key)
        prompt3 = await validator_manager.next(AWS_SECRET_ACCESS_KEY)
        self.assertEqual(prompt3, AWS_VALIDATORS[2].prompt)
        print('test_input_correct step3 pass')

        with self.assertRaises(SessionFinished):
            print(f'[test_input_correct] 67 {validator_manager.current_idx}')
            validator_manager = await ValidatorManager.load_validator(key)
            await validator_manager.next(REGION_NAME)
        print('test_input_correct step4 pass')

    async def test_input_invalid(self):
        key = CacheKeys.aws_validator_key('test_input_invalid')
        validator_manager = self._init_validator(key)
        prompt1 = await validator_manager.next()
        self.assertEqual(prompt1, AWS_VALIDATORS[0].prompt)
        print('test_input_invalid step1 pass')
        
        validator_manager = await ValidatorManager.load_validator(key)
        prompt2 = await validator_manager.next(AWS_ACCESS_KEY_ID)
        self.assertEqual(prompt2, AWS_VALIDATORS[1].prompt)
        print('test_input_invalid step2 pass')

        validator_manager = await ValidatorManager.load_validator(key)
        prompt3 = await validator_manager.next(AWS_SECRET_ACCESS_KEY)
        self.assertEqual(prompt3, AWS_VALIDATORS[2].prompt)
        print('test_input_invalid step3 pass')

        with self.assertRaises(ValidatorInvalidInput):
            print(f'[test_input_invalid] 67 {validator_manager.current_idx}')
            validator_manager = await ValidatorManager.load_validator(key)
            await validator_manager.next('invalid-region-name')


if __name__ == '__main__':
    unittest.main()
