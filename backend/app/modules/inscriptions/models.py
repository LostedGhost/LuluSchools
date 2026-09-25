import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatutInscription(str, enum.Enum):
    EN_ATTENTE_CONSENTEMENT_PARENTAL = "en_attente_consentement_parental"
    SOUMISE = "soumise"
    VALIDEE = "validee"
    REJETEE = "rejetee"


class Nationalite(str, enum.Enum):
    NATIONALE = "nationale"
    ETRANGERE = "etrangere"


class Eleve(Base):
    __tablename__ = "eleves"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    date_naissance: Mapped[date] = mapped_column(Date)
    nationalite: Mapped[Nationalite] = mapped_column(Enum(Nationalite), default=Nationalite.NATIONALE)
    matricule: Mapped[str | None] = mapped_column(String(30), unique=True, index=True, nullable=True)
    tuteur_id: Mapped[str | None] = mapped_column(ForeignKey("tuteurs.utilisateur_id"), nullable=True)
    utilisateur_id: Mapped[str | None] = mapped_column(
        ForeignKey("utilisateurs.id"), unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    inscriptions: Mapped[list["Inscription"]] = relationship(back_populates="eleve")


class Inscription(Base):
    __tablename__ = "inscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    statut: Mapped[StatutInscription] = mapped_column(Enum(StatutInscription))
    consentement_parental_horodatage: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    motif_rejet: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    eleve: Mapped[Eleve] = relationship(back_populates="inscriptions")
