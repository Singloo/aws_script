from datetime import date
from typing import TypedDict, Callable
from bson.objectid import ObjectId


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


class MongoMetadata(TypedDict):
    _id: ObjectId
    created_at: date
    updated_at: date


class AwsCrediential(MongoMetadata):
    region_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    alias: str
    user_id: ObjectId
    encrypted: bool


class Ec2Instance(MongoMetadata):
    outline_token: str
    outline_port: str
    instance_id: str
    alias: str
    default: bool
    user_id: ObjectId
    aws_crediential_id: ObjectId
    encrypted: bool


class User(MongoMetadata):
    wechat_id: str


class Ec2Status(MongoMetadata):
    ec2_id: ObjectId
    status: str
    ip: str
    last_modified_by: ObjectId


class Ec2OperationLog(MongoMetadata):
    ec2_id: ObjectId
    command: str
    triggered_by: ObjectId
    success: bool
    started_at: date
    finished_at: date
