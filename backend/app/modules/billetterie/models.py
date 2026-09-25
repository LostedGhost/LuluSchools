import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatutEvenement(str, enum.Enum):
    OUVERT = "ouvert"
    ANNULE = "annule"


class StatutBillet(str, enum.Enum):
    ACHETE = "achete"
    VALIDE = "valide"
    EXPIRE = "expire"
    REMBOURSE = "rembourse"


class Evenement(Base):
    """UC-17 : cree par l'A+, qui peut deleguer la gestion a un 'Parrain d'evenement'
    (parrain_utilisateur_id) - meme droits que l'A+ mais uniquement sur cet evenement
    precis, pas un role RBAC global (voir docs/diagrammes-uml-phase2-3.md)."""

    __tablename__ = "evenements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    titre: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    lieu: Mapped[str] = mapped_column(String(200))
    date_heure: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacite_max: Mapped[int] = mapped_column(Integer)
    prix_billet: Mapped[float] = mapped_column(Float, default=0)
    statut: Mapped[StatutEvenement] = mapped_column(Enum(StatutEvenement), default=StatutEvenement.OUVERT)
    parrain_utilisateur_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class BilletEvenement(Base):
    __tablename__ = "billets_evenement"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    evenement_id: Mapped[str] = mapped_column(ForeignKey("evenements.id"), index=True)
    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    statut: Mapped[StatutBillet] = mapped_column(Enum(StatutBillet), default=StatutBillet.ACHETE)
    prix_paye: Mapped[float] = mapped_column(Float)
    paiement_confirme: Mapped[bool] = mapped_column(Boolean, default=False)
    kkiapay_transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
