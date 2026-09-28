import httpx
from fastapi import UploadFile, status

from app.core.config import settings
from app.core.deps import api_error

MO = 1024 * 1024
TYPES_IMAGE = frozenset({"image/png", "image/jpeg", "image/webp"})
TYPES_DOCUMENT = TYPES_IMAGE | {"application/pdf"}
_TAILLE_BLOC = 1024 * 1024


class FileStorageError(Exception):
    """Levee quand LuluFiles refuse ou ne peut pas traiter une operation sur un fichier."""


def lire_upload_borne(fichier: UploadFile, max_octets: int, types_autorises: frozenset[str] | set[str] | None = None) -> bytes:
    """Lit un fichier televerse par blocs, sans jamais charger plus que `max_octets` en
    memoire (le plan Render gratuit n'a que 512 Mo), et refuse un type non attendu.
    Synchrone : a appeler depuis un endpoint `def` (execute dans le pool de threads)."""
    type_contenu = (fichier.content_type or "").split(";")[0].strip().lower()
    if types_autorises is not None and type_contenu not in types_autorises:
        raise api_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "type_fichier_refuse",
            f"Type de fichier non accepté ({type_contenu or 'inconnu'}). Types acceptés : {', '.join(sorted(types_autorises))}.",
        )
    morceaux: list[bytes] = []
    total = 0
    while True:
        bloc = fichier.file.read(_TAILLE_BLOC)
        if not bloc:
            break
        total += len(bloc)
        if total > max_octets:
            raise api_error(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "fichier_trop_volumineux",
                f"Fichier limité à {max_octets // MO} Mo.",
            )
        morceaux.append(bloc)
    if total == 0:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "fichier_vide", "Le fichier reçu est vide.")
    return b"".join(morceaux)


class LuluFilesClient:
    """Client minimal pour LuluFiles (voir ADR-003). Un seul disque, stockage a plat :
    le modele relationnel de LuluSchools reste la source de verite de l'organisation."""

    def __init__(self) -> None:
        self._base_url = settings.lulufiles_base_url
        self._headers = {"X-API-Key": settings.lulufiles_api_key}

    def upload(self, content: bytes, filename: str, content_type: str) -> str:
        try:
            response = httpx.post(
                f"{self._base_url}/files/upload",
                headers=self._headers,
                files={"upload": (filename, content, content_type)},
                timeout=httpx.Timeout(connect=15.0, read=120.0, write=120.0, pool=30.0),
            )
        except httpx.HTTPError as exc:
            raise FileStorageError("Impossible de contacter LuluFiles.") from exc

        if response.status_code not in (201, 202):
            raise FileStorageError(f"LuluFiles a refusé l'upload (statut {response.status_code}).")

        try:
            return response.json()["id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise FileStorageError("Réponse LuluFiles inattendue à l'upload.") from exc

    def get_signed_link(self, file_id: str, disposition: str = "attachment") -> str:
        try:
            response = httpx.post(
                f"{self._base_url}/files/{file_id}/link",
                headers=self._headers,
                json={"disposition": disposition},
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise FileStorageError("Impossible de contacter LuluFiles.") from exc

        if response.status_code != 200:
            raise FileStorageError(f"LuluFiles a refusé la demande de lien (statut {response.status_code}).")

        try:
            return self._base_url + response.json()["url"]
        except (ValueError, KeyError, TypeError) as exc:
            raise FileStorageError("Réponse LuluFiles inattendue à la demande de lien.") from exc


def get_files_client() -> LuluFilesClient:
    return LuluFilesClient()
