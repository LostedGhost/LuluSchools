import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatutDemandeActe(str, enum.Enum):
    SOUMISE = "soumise"
    EN_TRAITEMENT = "en_traitement"
    ACCEPTEE = "acceptee"
    REJETEE = "rejetee"


class TypeActeAcademique(Base):
    """UC-10 : catalogue configurable par etablissement (revise a partir d'un exemple
    reel de bareme universitaire - IFRI, voir cas-utilisation-phase-1.md). Chaque
    etablissement definit ses propres types (nom, prix, pieces requises en texte libre,
    condition d'eligibilite optionnelle)."""

    __tablename__ = "types_acte_academique"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    nom: Mapped[str] = mapped_column(String(200))
    prix: Mapped[float] = mapped_column(Float, default=0)
    pieces_requises: Mapped[str] = mapped_column(Text)
    condition_eligibilite: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DemandeActeAcademique(Base):
    __tablename__ = "demandes_acte_academique"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    type_acte_id: Mapped[str | None] = mapped_column(ForeignKey("types_acte_academique.id"), nullable=True)
    est_reclamation: Mapped[bool] = mapped_column(Boolean, default=False)
    reference_evaluation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    statut: Mapped[StatutDemandeActe] = mapped_column(Enum(StatutDemandeActe), default=StatutDemandeActe.SOUMISE)
    paiement_confirme: Mapped[bool] = mapped_column(Boolean, default=False)
    motif_rejet: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
