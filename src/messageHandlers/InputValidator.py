from src.types import ValidatorFunc
import time
from src.types.type import CachedData
from src.utils.util import list_every
from src.db.redis import pickle_get, pickle_save


class SessionExpiredException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Session expired, try again.', *args)


class SessionFinished(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Session finished', *args)


class ValidatorInvalidInput(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Invalid input', *args)


class ValidatorInvalidAndExceedMaximumTimes(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Exceeded maxium times', *args)


class ValidatorDataCorupted(Exception):
    '''
        Data corupted
    '''

    def __init__(self, *args: object) -> None:
        super().__init__('Data corupted', *args)


class Validator():
    # prompt msg
    _prompt: str
    # prompt msg when input is invalid
    _invalid_prompt: str
    # attribute name
    _attribute_name: str
    # test if input is valid
    _validator: ValidatorFunc
    # input value from user
    _value: str | None
    # retried times
    _times: int
    # should encrypt value
    _encrypt: bool

    def __init__(self, prompt: str, invalid_prompt: str, attribute_name: str, validator: ValidatorFunc, encrypt: bool = False) -> None:
        self._prompt = prompt
        self._invalid_prompt = invalid_prompt
        self._attribute_name = attribute_name
        self._validator = validator
        self._encrypt = encrypt

        self._value = None
        self._times = 0
        self.MAX_TIMES = 3

    @property
    def value(self):
        return self._value

    @property
    def is_max_times_exceeded(self):
        return self._times > self.MAX_TIMES

    @property
    def prompt(self):
        return self._prompt

    @property
    def invalid_prompt(self):
        return self._invalid_prompt

    @value.setter
    def value(self, newValue: str):
        self._times += 1
        try:
            if not isinstance(newValue, str):
                raise ValidatorInvalidInput
            if not self._validator(newValue):
                raise ValidatorInvalidInput
        except ValidatorInvalidInput:
            if self._times >= self.MAX_TIMES:
                # exceed maximum times error only happened when input is invalid
                raise ValidatorInvalidAndExceedMaximumTimes
            raise
        self._value = newValue


class ValidatorManager():
    @classmethod
    def init_db_input_validator(cls, validators: list[Validator], uniq_key: str,  col_name: str):
        return cls(validators, uniq_key, col_name=col_name)

    @staticmethod
    async def load_validator(uniq_key: str):
        return await pickle_get(uniq_key)

    def __init__(self, validators: list[Validator], uniq_key: str, **kwargs) -> None:
        self._validators = validators
        self.current_idx = 0
        # seconds
        self.start_time = time.time()
        self.session_duration = 5*60
        self.end_time = self.start_time + self.session_duration

        self.uniq_key = uniq_key
        # will return when validator finished
        self.other_args = kwargs

    @property
    def current_validator(self):
        return self._validators[self.current_idx]

    @property
    def is_expired(self):
        return time.time() > self.end_time

    @property
    def is_finished(self):
        is_max_idx = self.current_idx == len(self._validators)

        def _every_validator_got_answer(validator: Validator):
            return validator.value != None
        is_all_value_filled = list_every(
            self._validators, _every_validator_got_answer)

        if (int(is_max_idx) + int(is_all_value_filled)) == 1:
            raise ValidatorDataCorupted
        return is_max_idx & is_all_value_filled

    def _get_one(self):
        # expired?
        if self.is_expired:
            raise SessionExpiredException
        # finished?
        if self.is_finished:
            raise SessionFinished
        # return current
        return self.current_validator

    async def save(self):
        '''
            increase current_index
            save to redis
        '''
        self.current_idx += 1
        await pickle_save(self.uniq_key, self)

    def get_prompt(self):
        validator = self._get_one()
        return validator.prompt

    def collect(self):
        pass

    def validate_input(self, input: str):
        validator = self._get_one()
        validator.value = input

    async def next(self, input: str | None = None):
        if input is not None:
            self.validate_input(input)
            await self.save()
        return self.get_prompt()
