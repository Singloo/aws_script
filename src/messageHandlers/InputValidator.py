from src.types import ValidatorFunc, Validator


class InputValidator():
    def __init__(self, validators: list[Validator]) -> None:
        self._validators = validators
        self.current_idx = 0
        
