from typing import TypedDict, Callable


class CachedData(TypedDict):
    instance_id: str


ValidatorFunc = Callable[[str], bool]


class Validator(TypedDict):
    # prompt msg
    prompt: str
    # prompt msg when input is invalid
    invalid_prompt: str
    # attribute name
    attribute_name: str
    # test if input is valid
    validator: ValidatorFunc
    # input value from user
    value: str | None
    # retried times
    times: int
    # should encrypt value
    encrypt: bool
