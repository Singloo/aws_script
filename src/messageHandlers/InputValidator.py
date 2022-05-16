from tkinter import E
from src.types import ValidatorFunc
import time
from src.utils.util import list_every, list_reduce
from src.db.redis import pickle_get, pickle_save
import src.utils.crypto as Crypto


class SessionExpired(Exception):
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


class NoSuchSession(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('No such session', *args)


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
        if self._encrypt and self._value != None:
            return Crypto.encrypt(self._value)
        return self._value

    @property
    def is_max_times_exceeded(self):
        return self._times >= self.MAX_TIMES

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
            if self.is_max_times_exceeded:
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
        ins = await pickle_get(uniq_key)
        if ins is None:
            raise NoSuchSession
        return ins

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
        return is_max_idx and is_all_value_filled

    def check_if_continue(self):
        # expired?
        if self.is_expired:
            raise SessionExpired
        # finished?
        if self.is_finished:
            raise SessionFinished

    @property
    def get_session_left_time(self):
        return round(self.end_time - time.time())

    async def save(self):
        '''
            increase current_index
            save to redis
        '''
        if self.get_session_left_time < 1:
            return
        await pickle_save(self.uniq_key, self, exp=self.get_session_left_time)

    def get_prompt(self):
        validator = self.current_validator
        return validator.prompt

    def collect(self):
        def _extract_value(prev, curr: Validator):
            return {
                **prev,
                curr._attribute_name: curr.value
            }
        return {
            'other_args': self.other_args,
            'data': list_reduce(self._validators, _extract_value, {})
        }

    def validate_input(self, input: str):
        validator = self.current_validator
        validator.value = input
        self.current_idx += 1

    async def next(self, input: str | None = None):
        '''
        1. if has input, check if input is valid. valid ? current_idx + 1 : raise error
        2. check if session if finished or expired. True ? raise error
        3. save session
        4. return current or next validator prompt
        '''
        try:
            if input is not None:
                self.validate_input(input)
        finally:
            try:
                self.check_if_continue()
            finally:
                await self.save()
        return self.get_prompt()
