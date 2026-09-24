import httpx

from app.core.config import settings


class FileStorageError(Exception):
    """Levee quand LuluFiles refuse ou ne peut pas traiter une operation sur un fichier."""


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
            raise FileStorageError(f"LuluFiles a refuse l'upload (statut {response.status_code}).")

        return response.json()["id"]

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
            raise FileStorageError(f"LuluFiles a refuse la demande de lien (statut {response.status_code}).")

        return self._base_url + response.json()["url"]


def get_files_client() -> LuluFilesClient:
    return LuluFilesClient()
