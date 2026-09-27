import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import jwt

from app.core.config import settings

_password_hasher = PasswordHasher()

JWT_ALGORITHM = "HS256"

# Hash d'un mot de passe jetable : verifie quand l'identifiant est inconnu, pour que la
# duree de reponse du login ne revele pas l'existence d'un compte.
_HASH_FACTICE = _password_hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_password_factice(password: str) -> None:
    verify_password(password, _HASH_FACTICE)


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_salt() -> str:
    return secrets.token_hex(16)


def hash_otp_code(code: str, salt: str) -> str:
    return hmac.new(salt.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


def otp_correspond(code: str, salt: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_otp_code(code, salt), code_hash)


def generate_temporary_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isupper() for c in candidate) and any(c.isdigit() for c in candidate):
            return candidate


def create_access_token(subject: str, role: str) -> str:
    maintenant = datetime.now(timezone.utc)
    expire = maintenant + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "type": "access", "iat": maintenant, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def marqueur_session(mot_de_passe_modifie_le: datetime | None) -> int:
    """Empreinte du dernier changement de mot de passe, embarquee dans chaque refresh
    token : elle change a chaque changement/reinitialisation, ce qui invalide d'un coup
    toutes les sessions ouvertes avant (comparaison exacte, sans ambiguite a la seconde)."""
    if mot_de_passe_modifie_le is None:
        return 0
    if mot_de_passe_modifie_le.tzinfo is None:
        mot_de_passe_modifie_le = mot_de_passe_modifie_le.replace(tzinfo=timezone.utc)
    return int(mot_de_passe_modifie_le.timestamp() * 1000)


def create_refresh_token(subject: str, mot_de_passe_modifie_le: datetime | None = None) -> str:
    maintenant = datetime.now(timezone.utc)
    expire = maintenant + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": subject,
        "type": "refresh",
        "sm": marqueur_session(mot_de_passe_modifie_le),
        "iat": maintenant,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])


def refresh_token_revoque(payload: dict, mot_de_passe_modifie_le: datetime | None) -> bool:
    return int(payload.get("sm", 0)) != marqueur_session(mot_de_passe_modifie_le)
