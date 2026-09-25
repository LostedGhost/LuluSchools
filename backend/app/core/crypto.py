import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    """Derive une cle Fernet valide (32 octets urlsafe-base64) a partir du secret
    CASIER_JUDICIAIRE_ENCRYPTION_KEY, quel que soit son format d'origine : le
    `generateValue: true` de Render produit un base64 standard (pas forcement
    urlsafe), qu'un simple `Fernet(settings...)` rejetterait."""
    digest = hashlib.sha256(settings.casier_judiciaire_encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def chiffrer_bytes(contenu: bytes) -> bytes:
    return _fernet().encrypt(contenu)


def dechiffrer_bytes(contenu_chiffre: bytes) -> bytes:
    return _fernet().decrypt(contenu_chiffre)
