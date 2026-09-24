import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt

from app.core.config import settings

_password_hasher = PasswordHasher()

JWT_ALGORITHM = "HS256"


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


def generate_temporary_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isupper() for c in candidate) and any(c.isdigit() for c in candidate):
            return candidate


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {"sub": subject, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
