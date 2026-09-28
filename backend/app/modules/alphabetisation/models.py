import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InscriptionAlphabetisation(Base):
    """Lot 7.7 (PAG, action 4) : un adulte suit une classe d'un centre d'alphabetisation
    avec SON compte (tuteur/parent) - pas de nouveau compte, pas de matricule scolaire,
    pas de consentement parental (majeur). Le parent peut ainsi apprendre sur la meme
    plateforme que ses enfants."""

    __tablename__ = "inscriptions_alphabetisation"
    __table_args__ = (UniqueConstraint("utilisateur_id", "classe_id", name="uq_alphabetisation_utilisateur_classe"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
