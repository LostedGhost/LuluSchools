import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ServiceControle(str, enum.Enum):
    TRANSPORT = "transport"
    CANTINE = "cantine"
    EVENEMENT = "evenement"


class DesignationControleur(Base):
    """UC-11/UC-12/UC-17 : role temporaire attribue explicitement par l'A+, une
    designation distincte par service (delegue UC-12) - un meme utilisateur peut
    cumuler plusieurs designations. `evenement_id` n'est pas une vraie ForeignKey
    (le module billetterie est ajoute apres celui-ci, la table `evenements` n'existe
    pas encore a cette migration) : rattachement verifie au niveau applicatif."""

    __tablename__ = "designations_controleur"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    service: Mapped[ServiceControle] = mapped_column(Enum(ServiceControle))
    evenement_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
