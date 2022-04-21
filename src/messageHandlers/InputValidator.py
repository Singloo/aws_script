from src.types import ValidatorFunc, Validator
import time


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


    
