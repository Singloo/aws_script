from datetime import datetime
from typing import Any, TypedDict, Callable, Optional
from xmlrpc.client import boolean
from bson.objectid import ObjectId
from enum import Enum


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
    created_at: datetime
    updated_at: datetime


class AwsCrediential(MongoMetadata):
    region_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    alias: str
    user_id: ObjectId
    encrypted: bool


class Ec2Instance(MongoMetadata):
    outline_token: str | None
    outline_port: str | None
    instance_id: str
    alias: str
    default: bool
    user_id: ObjectId
    aws_crediential_id: ObjectId
    encrypted: bool


class User(MongoMetadata):
    wechat_id: str
    activated_at: datetime


class Ec2Status(MongoMetadata):
    ec2_id: ObjectId
    status: str
    ip: str
    modified_by: ObjectId
    last_command: str


class Ec2OperationLogStatus(Enum):
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'
    EXCEED_MAX_RUNTIME = 'exceed_max_runtime'


class Ec2OperationLog(MongoMetadata):
    ec2_id: ObjectId
    command: str
    triggered_by: ObjectId
    success: bool
    started_at: datetime
    finished_at: datetime | None
    status: Ec2OperationLogStatus
    error: Any | None


class Ec2Cron(MongoMetadata):
    ec2_id: ObjectId
    command: str
    created_by: ObjectId
    hour: int
    minute: int
    active: bool
