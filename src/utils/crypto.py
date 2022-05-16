from cryptography.fernet import Fernet
from src.utils.constants import CRYPTO_KEY

f = Fernet(CRYPTO_KEY)


def encrypt(msg: str) -> str:
    return f.encrypt(msg.encode('utf-8')).decode('utf-8')


def decrypt(data: str) -> str:
    return f.decrypt(data.encode('utf-8')).decode('utf-8')
