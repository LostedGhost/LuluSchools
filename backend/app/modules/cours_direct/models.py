import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatutSessionLive(str, enum.Enum):
    PLANIFIEE = "planifiee"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"


class SessionLive(Base):
    __tablename__ = "sessions_live"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignants.utilisateur_id"), index=True)
    date_heure: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    statut: Mapped[StatutSessionLive] = mapped_column(Enum(StatutSessionLive), default=StatutSessionLive.PLANIFIEE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ConsentementCameraLive(Base):
    """UC-16 : consentement explicite et horodate du tuteur, distinct du consentement
    d'inscription (extension d'Art. 446) - un seul par eleve, valable pour toutes les
    sessions live futures une fois donne."""

    __tablename__ = "consentements_camera_live"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), unique=True, index=True)
    tuteur_id: Mapped[str] = mapped_column(ForeignKey("tuteurs.utilisateur_id"))
    date_consentement: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ParticipationLive(Base):
    __tablename__ = "participations_live"
    __table_args__ = (UniqueConstraint("session_id", "eleve_utilisateur_id", name="uq_participation_live"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_live.id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    camera_autorisee: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
