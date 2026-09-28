from datetime import datetime, timedelta, timezone

from fastapi import Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import api_error
from app.modules.identite.models import TentativeLimitee

_CONSERVATION = timedelta(days=1)


def adresse_client(request: Request) -> str:
    """Derriere le proxy Render (et le rewrite Vercel), l'IP reelle est le premier
    maillon de X-Forwarded-For. Falsifiable par un appel direct au service Render : les
    limites par identifiant (non falsifiables) restent donc la protection principale."""
    transmis = request.headers.get("x-forwarded-for")
    if transmis:
        return transmis.split(",")[0].strip()
    return request.client.host if request.client else "inconnu"


def _depasse(db: Session, cle: str, maximum: int, fenetre_secondes: float) -> bool:
    depuis = datetime.now(timezone.utc) - timedelta(seconds=fenetre_secondes)
    nombre = (
        db.query(func.count(TentativeLimitee.id))
        .filter(TentativeLimitee.cle == cle, TentativeLimitee.created_at >= depuis)
        .scalar()
    )
    return (nombre or 0) >= maximum


_MESSAGE_PAR_DEFAUT = "Trop de tentatives. Veuillez patienter quelques minutes avant de réessayer."


def verifier_limite(
    db: Session, cle: str, maximum: int, fenetre_secondes: float, message: str = _MESSAGE_PAR_DEFAUT
) -> None:
    if not settings.rate_limit_enabled:
        return
    if _depasse(db, cle[:255], maximum, fenetre_secondes):
        raise api_error(status.HTTP_429_TOO_MANY_REQUESTS, "trop_de_tentatives", message)


def enregistrer_echec(db: Session, cle: str) -> None:
    """Commit immediat : l'appelant leve le plus souvent une erreur juste apres, ce qui
    annulerait sinon l'enregistrement. A n'appeler que sans modification metier en attente."""
    if not settings.rate_limit_enabled:
        return
    cle = cle[:255]
    db.query(TentativeLimitee).filter(
        TentativeLimitee.cle == cle, TentativeLimitee.created_at < datetime.now(timezone.utc) - _CONSERVATION
    ).delete(synchronize_session=False)
    db.add(TentativeLimitee(cle=cle))
    db.commit()


def consommer(
    db: Session, cle: str, maximum: int, fenetre_secondes: float, message: str = _MESSAGE_PAR_DEFAUT
) -> None:
    """Verifie puis compte une tentative (actions limitees a chaque appel, succes ou
    echec : inscription, renvoi de code, mot de passe oublie)."""
    verifier_limite(db, cle, maximum, fenetre_secondes, message)
    enregistrer_echec(db, cle)


def reinitialiser(db: Session, cle: str) -> None:
    if not settings.rate_limit_enabled:
        return
    db.query(TentativeLimitee).filter(TentativeLimitee.cle == cle[:255]).delete(synchronize_session=False)
    db.commit()
