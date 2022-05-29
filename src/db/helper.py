
from typing import Any
import src.utils.crypto as Crypto


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
