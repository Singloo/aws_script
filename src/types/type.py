from typing import TypedDict, Callable


class CachedData(TypedDict):
    instance_id: str


ValidatorFunc = Callable[[str], bool]


class Validator(TypedDict):
    prompt: str
    attribute_name: str
    validator: ValidatorFunc
    value: str | None
