
from typing import Any
from src.types.type import AwsCrediential, Ec2Instance
import src.utils.crypto as Crypto
from pymongo.cursor import Cursor


def ensure_decrypted(data: dict, keys_to_decrypt: list[str] = []) -> Any:
    if data.get('encrypted', False) == False:
        return data
    return {k: v if k not in keys_to_decrypt else Crypto.decrypt(v) for k, v in data.items()}


def is_int(some_str: str):
    try:
        int(some_str)
        return True
    except ValueError:
        return False


def decrypt_aws_crediential(doc: AwsCrediential):
    if doc is None:
        return None
    return ensure_decrypted(doc, ['aws_access_key_id', 'aws_secret_access_key'])


def decrypt_aws_crediential_cursor(cursor: Cursor):
    return list(map(decrypt_aws_crediential, list(cursor)))


def decrypt_ec2_instance(doc: Ec2Instance):
    if doc is None:
        return None
    return ensure_decrypted(doc, ['instance_id'])


def decrypt_ec2_instance_cursor(cursor: Cursor):
    return list(map(decrypt_ec2_instance, list(cursor)))
