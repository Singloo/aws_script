import asyncio
import unittest
from .InputValidator import ValidatorManager, Validator, SessionFinished, SessionExpired, ValidatorInvalidInput, ValidatorInvalidAndExceedMaximumTimes
from src.utils.util import re_strict_match, re_test
from functools import partial
from src.utils.constants import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME
from src.db.redis import CacheKeys
from src.utils.crypto import decrypt

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
        self.maxDiff = None

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

        validator_manager = await ValidatorManager.load_validator(key)
        prompt2 = await validator_manager.next(AWS_ACCESS_KEY_ID)
        self.assertEqual(prompt2, AWS_VALIDATORS[1].prompt)

        validator_manager = await ValidatorManager.load_validator(key)
        prompt3 = await validator_manager.next(AWS_SECRET_ACCESS_KEY)
        self.assertEqual(prompt3, AWS_VALIDATORS[2].prompt)

        with self.assertRaises(SessionFinished):
            validator_manager = await ValidatorManager.load_validator(key)
            await validator_manager.next(REGION_NAME)
        validator_manager: ValidatorManager = await ValidatorManager.load_validator(key)
        res = validator_manager.collect()
        self.assertDictEqual(
            res['other_args'],
            {'col_name': 'aws'}
        )
        self.assertEqual(
            decrypt(res['data']['aws_key_id']), AWS_ACCESS_KEY_ID)
        self.assertEqual(
            decrypt(res['data']['aws_secret_access_key']), AWS_SECRET_ACCESS_KEY)

    async def test_input_invalid(self):
        key = CacheKeys.aws_validator_key('test_input_invalid')
        validator_manager = self._init_validator(key)
        prompt1 = await validator_manager.next()
        self.assertEqual(prompt1, AWS_VALIDATORS[0].prompt)

        validator_manager = await ValidatorManager.load_validator(key)
        prompt2 = await validator_manager.next(AWS_ACCESS_KEY_ID)
        self.assertEqual(prompt2, AWS_VALIDATORS[1].prompt)

        validator_manager = await ValidatorManager.load_validator(key)
        prompt3 = await validator_manager.next(AWS_SECRET_ACCESS_KEY)
        self.assertEqual(prompt3, AWS_VALIDATORS[2].prompt)

        with self.assertRaises(ValidatorInvalidInput):
            validator_manager = await ValidatorManager.load_validator(key)
            await validator_manager.next('invalid-region-name')

    async def test_exceed_maximum_times(self):
        key = CacheKeys.aws_validator_key('test_exceed_maximum_times')
        validator_manager = self._init_validator(key)
        prompt1 = await validator_manager.next()
        self.assertEqual(prompt1, AWS_VALIDATORS[0].prompt)

        with self.assertRaises(ValidatorInvalidInput):
            validator_manager = await ValidatorManager.load_validator(key)
            await validator_manager.next('invalid-secret')

        with self.assertRaises(ValidatorInvalidInput):
            validator_manager = await ValidatorManager.load_validator(key)
            await validator_manager.next('invalid-secret2')

        with self.assertRaises(ValidatorInvalidAndExceedMaximumTimes):
            validator_manager: ValidatorManager = await ValidatorManager.load_validator(key)
            await validator_manager.next('invalid-secret')

    async def test_session_expired(self):
        key = CacheKeys.aws_validator_key('test_session_expired')
        validator_manager = self._init_validator(key)
        validator_manager.end_time = validator_manager.start_time + 1

        prompt1 = await validator_manager.next()
        self.assertEqual(prompt1, AWS_VALIDATORS[0].prompt)

        validator_manager = await ValidatorManager.load_validator(key)
        prompt2 = await validator_manager.next(AWS_ACCESS_KEY_ID)
        self.assertEqual(prompt2, AWS_VALIDATORS[1].prompt)

        validator_manager = await ValidatorManager.load_validator(key)
        prompt3 = await validator_manager.next(AWS_SECRET_ACCESS_KEY)
        self.assertEqual(prompt3, AWS_VALIDATORS[2].prompt)

        with self.assertRaises(SessionExpired):
            validator_manager = await ValidatorManager.load_validator(key)
            await asyncio.sleep(1)
            await validator_manager.next(REGION_NAME)


if __name__ == '__main__':
    unittest.main()
