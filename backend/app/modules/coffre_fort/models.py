import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModuleDepenseCoffreFort(str, enum.Enum):
    MICRO_JOB = "micro_job"
    MARKETPLACE = "marketplace"
    ACTE = "acte"


class StatutValidationParentale(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    APPROUVEE = "approuvee"
    REFUSEE = "refusee"


class PlafondFamilial(Base):
    """UC-35.1 : configuration opt-in, un seul enregistrement par enfant, geree
    exclusivement par son tuteur. L'absence de ligne signifie "aucune limite" (le
    comportement actuel, sans Coffre-fort, reste inchange) - jamais un plafond
    implicite a zero (UC-35.4)."""

    __tablename__ = "plafonds_familiaux"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tuteur_id: Mapped[str] = mapped_column(ForeignKey("tuteurs.utilisateur_id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), unique=True, index=True)
    plafond_hebdomadaire: Mapped[float | None] = mapped_column(Float, nullable=True)
    seuil_validation: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ValidationParentale(Base):
    """UC-35.2 : s'intercale entre la creation d'une offre/reservation/demande et
    l'amorcage de son paiement, quand le montant depasse le seuil de validation defini
    par le tuteur - jamais un blocage silencieux, le paiement reste possible des que le
    tuteur statue. `reference_id` n'est PAS une vraie ForeignKey (comme
    DesignationControleur.evenement_id) : selon `module`, elle designe une
    OffreMicroJob, une TransactionMarketplace ou une DemandeActeAcademique."""

    __tablename__ = "validations_parentales"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tuteur_id: Mapped[str] = mapped_column(ForeignKey("tuteurs.utilisateur_id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    module: Mapped[ModuleDepenseCoffreFort] = mapped_column(Enum(ModuleDepenseCoffreFort))
    reference_id: Mapped[str] = mapped_column(String(36), index=True)
    montant: Mapped[float] = mapped_column(Float)
    statut: Mapped[StatutValidationParentale] = mapped_column(
        Enum(StatutValidationParentale), default=StatutValidationParentale.EN_ATTENTE
    )
    motif_refus: Mapped[str | None] = mapped_column(Text, nullable=True)
    decidee_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AlerteDepassementPlafond(Base):
    """UC-35.2 : depassement du plafond hebdomadaire -> simple notification passive
    consultable par le tuteur (meme logique de consultation qu'AlerteElProfessor),
    l'enfant n'est jamais bloque par ce mecanisme (seul le seuil de validation bloque)."""

    __tablename__ = "alertes_depassement_plafond"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tuteur_id: Mapped[str] = mapped_column(ForeignKey("tuteurs.utilisateur_id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    module: Mapped[ModuleDepenseCoffreFort] = mapped_column(Enum(ModuleDepenseCoffreFort))
    montant_semaine: Mapped[float] = mapped_column(Float)
    plafond: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
