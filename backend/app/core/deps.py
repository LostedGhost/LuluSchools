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


def get_current_active_user(utilisateur: Utilisateur = Depends(get_current_user)) -> Utilisateur:
    """Comme get_current_user, mais bloque un compte dont le mot de passe temporaire
    (eleve/admin etablissement provisionnes) n'a pas encore ete change - sauf pour
    /me et /auth/change-password, qui utilisent get_current_user directement pour
    rester accessibles pendant ce changement obligatoire."""
    if utilisateur.mot_de_passe_temporaire:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "changement_mot_de_passe_requis",
            "Vous devez changer votre mot de passe temporaire avant de continuer (POST /auth/change-password).",
        )
    return utilisateur


def require_roles(*roles: RoleUtilisateur):
    def _dependency(utilisateur: Utilisateur = Depends(get_current_active_user)) -> Utilisateur:
        if utilisateur.role not in roles:
            raise api_error(
                status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action."
            )
        return utilisateur

    return _dependency


def verifier_portee_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    """A appeler apres un require_roles(...ADMIN_ETABLISSEMENT, ADMIN_MINISTERIEL) sur un
    endpoint de gestion d'etablissement : centralise la regle A++ / A+ pour eviter que
    chaque module reimplemente sa propre verification (constat d'audit : 4 copies
    independantes bloquaient toutes A++ par erreur, cf. commit qui introduit cette
    fonction). ADMIN_MINISTERIEL gere tous les etablissements sans restriction.
    ADMIN_ETABLISSEMENT doit administrer precisement l'etablissement vise. Tout autre
    role est refuse."""
    from app.modules.etablissements.models import AdminEtablissement

    if utilisateur.role == RoleUtilisateur.ADMIN_MINISTERIEL:
        return
    if utilisateur.role != RoleUtilisateur.ADMIN_ETABLISSEMENT:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action.")
    lien = db.get(AdminEtablissement, utilisateur.id)
    if lien is None or lien.etablissement_id != etablissement_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")
