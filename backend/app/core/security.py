import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_salt() -> str:
    return secrets.token_hex(16)


def hash_otp_code(code: str, salt: str) -> str:
    return hmac.new(salt.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()
