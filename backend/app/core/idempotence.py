"""Lot 7.5 (UC-80) — requetes rejouables sans double effet.

Sur un reseau instable, un envoi peut atteindre le serveur sans que la reponse revienne :
l'application le garde en file d'attente et le rejoue au retour du reseau, avec la meme
cle `X-Cle-Idempotence`. Le serveur memorise la premiere reponse reussie (2xx) de chaque
(utilisateur, cle) et la renvoie telle quelle aux rejeux : une absence, un message ou une
copie n'est jamais enregistre deux fois. Entrees conservees 7 jours.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request
from jose import JWTError
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import Base, get_session_factory
from app.core.security import decode_token

logger = logging.getLogger(__name__)

EN_TETE = "x-cle-idempotence"
CONSERVATION = timedelta(days=7)


class RequeteIdempotente(Base):
    __tablename__ = "requetes_idempotentes"

    empreinte: Mapped[str] = mapped_column(String(64), primary_key=True)
    statut_http: Mapped[int] = mapped_column(Integer)
    type_contenu: Mapped[str] = mapped_column(String(100))
    corps: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def _utilisateur(request: Request) -> str | None:
    autorisation = request.headers.get("authorization", "")
    if not autorisation.lower().startswith("bearer "):
        return None
    try:
        return str(decode_token(autorisation[7:]).get("sub") or "") or None
    except JWTError:
        return None


def _cle_valide(cle: str) -> bool:
    try:
        uuid.UUID(cle)
        return True
    except ValueError:
        return False


class IdempotenceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cle = request.headers.get(EN_TETE)
        if request.method != "POST" or not cle or not _cle_valide(cle):
            return await call_next(request)
        utilisateur = _utilisateur(request)
        if utilisateur is None:
            return await call_next(request)  # sans session, la route repondra 401 d'elle-meme
        empreinte = hashlib.sha256(f"{utilisateur}:{request.url.path}:{cle}".encode()).hexdigest()
        # Les tests redirigent la fabrique de sessions vers leur base (meme mecanisme que
        # les BackgroundTasks, voir database.get_session_factory).
        fabrique = request.app.dependency_overrides.get(get_session_factory, get_session_factory)()

        # Jamais bloquant : si la memoire des rejeux est indisponible (migration pas encore
        # appliquee, base saturee), la requete est traitee normalement, sans protection.
        db = fabrique()
        try:
            deja = db.get(RequeteIdempotente, empreinte)
        except SQLAlchemyError:
            logger.exception("Idempotence indisponible, requete traitee sans protection contre les rejeux")
            return await call_next(request)
        finally:
            db.close()
        if deja is not None:
            return Response(
                content=deja.corps, status_code=deja.statut_http, media_type=deja.type_contenu,
                headers={"X-Idempotence-Rejeu": "1"},
            )

        reponse = await call_next(request)
        if not 200 <= reponse.status_code < 300:
            return reponse
        corps = b"".join([morceau async for morceau in reponse.body_iterator])
        db = fabrique()
        try:
            db.query(RequeteIdempotente).filter(
                RequeteIdempotente.created_at < datetime.now(timezone.utc) - CONSERVATION
            ).delete(synchronize_session=False)
            db.merge(RequeteIdempotente(
                empreinte=empreinte, statut_http=reponse.status_code,
                type_contenu=reponse.headers.get("content-type", "application/json"), corps=corps.decode("utf-8", "replace"),
            ))
            db.commit()
        except SQLAlchemyError:
            logger.exception("Reponse non memorisee pour les rejeux")
            db.rollback()
        finally:
            db.close()
        return Response(content=corps, status_code=reponse.status_code, headers=dict(reponse.headers), media_type=reponse.media_type)
