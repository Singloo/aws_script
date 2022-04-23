from src.types import ValidatorFunc
import time
from src.types.type import CachedData
from src.utils.util import list_every


class SessionExpiredException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Session expired, try again.', *args)


class SessionFinished(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Session finished', *args)


class ValidatorInvalidInput(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Invalid input', *args)


class ValidatorExceedMaximumTimes(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Exceeded maxium times', *args)


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

    def __init__(self, prompt: str, invalid_prompt: str, attribute_name: str, validator: ValidatorFunc, encrypt: bool) -> None:
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

    @value.setter
    def value(self, newValue: str):
        self._times += 1
        if self.is_max_times_exceeded:
            raise ValidatorExceedMaximumTimes()
        if not isinstance(newValue, str):
            raise ValidatorInvalidInput()
        if not self._validator(newValue):
            raise ValidatorInvalidInput()
        self._value = newValue


class InputValidator():
    def __init__(self, validators: list[Validator]) -> None:
        self._validators = validators
        self.current_idx = 0
        # seconds
        self.start_time = time.time()
        self.session_duration = 5*60
        self.end_time = self.start_time + self.session_duration

    @property
    def current_validator(self):
        return self._validators[self.current_idx]

    @property
    def is_expired(self):
        return time.time() > self.end_time

    @property
    def is_finished(self):
        if self.current_idx < len(self._validators) - 1:
            return False

        def _every_validator_got_answer(validator: Validator):
            return validator.value != None

        return list_every(self._validators, _every_validator_got_answer)

    def get_one(self):
        if self.is_expired:
            raise SessionExpiredException()
        if self.is_finished:
            raise SessionFinished()
