from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.modules.identite.models import RoleUtilisateur, Utilisateur

_bearer_scheme = HTTPBearer(auto_error=False)


def api_error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": details or {}}},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    if credentials is None:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "non_authentifie", "Authentification requise.")
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "token_invalide", "Token invalide ou expire."
        ) from exc

    if payload.get("type") != "access":
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "token_invalide", "Ce token n'est pas un access token."
        )

    utilisateur = db.get(Utilisateur, payload.get("sub"))
    if utilisateur is None:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "utilisateur_introuvable", "Utilisateur introuvable."
        )
    return utilisateur


def require_roles(*roles: RoleUtilisateur):
    def _dependency(utilisateur: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if utilisateur.role not in roles:
            raise api_error(
                status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action."
            )
        return utilisateur

    return _dependency
