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


class StatutOffreMicroJob(str, enum.Enum):
    EN_ATTENTE_PAIEMENT = "en_attente_paiement"
    OUVERTE = "ouverte"
    FERMEE = "fermee"
    ANNULEE = "annulee"


class StatutMissionMicroJob(str, enum.Enum):
    EN_COURS = "en_cours"
    TERMINEE_DECLAREE = "terminee_declaree"
    VALIDEE = "validee"
    CONTESTEE = "contestee"
    REMBOURSEE = "remboursee"
    PAYEE = "payee"


class StatutContestationMicroJob(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    ACCEPTEE = "acceptee"
    REJETEE = "rejetee"


class OffreMicroJob(Base):
    """UC-18, modele "demande payee d'avance" : n'importe quel role authentifie
    (y compris Eleve) peut publier une offre EN TANT QUE CLIENT, a condition de payer
    le montant a la publication (sequestre immediat, avant meme qu'un prestataire ne
    soit trouve) - voir ADR-008 addendum. Un Eleve reste exclu du role de PRESTATAIRE
    (celui qui accepte l'offre et est remunere pour le travail) : c'est cette
    remuneration d'un mineur, pas le fait de payer pour un service, qui pose une
    question legale sur l'age minimum de travail (hors perimetre loi n 2017-20)."""

    __tablename__ = "offres_micro_job"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    client_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    titre: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    prix: Mapped[float] = mapped_column(Float)
    statut: Mapped[StatutOffreMicroJob] = mapped_column(
        Enum(StatutOffreMicroJob), default=StatutOffreMicroJob.EN_ATTENTE_PAIEMENT
    )
    paiement_confirme: Mapped[bool] = mapped_column(Boolean, default=False)
    kkiapay_transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MissionMicroJob(Base):
    """Sequestre "Option A" (ADR-008) : le paiement du client est encaisse sur le
    compte Kkiapay unique de LuluSchools DES LA PUBLICATION de l'offre (voir
    OffreMicroJob) - une mission n'existe donc jamais sans paiement deja confirme.
    Le reversement au prestataire (`reference_paiement_prestataire`) reste manuel."""

    __tablename__ = "missions_micro_job"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    offre_id: Mapped[str] = mapped_column(ForeignKey("offres_micro_job.id"), unique=True, index=True)
    prestataire_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    statut: Mapped[StatutMissionMicroJob] = mapped_column(
        Enum(StatutMissionMicroJob), default=StatutMissionMicroJob.EN_COURS
    )
    prix_paye: Mapped[float] = mapped_column(Float)
    paiement_confirme: Mapped[bool] = mapped_column(Boolean, default=False)
    kkiapay_transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    date_declaration_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_limite_validation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_paiement_prestataire: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ContestationMicroJob(Base):
    __tablename__ = "contestations_micro_job"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions_micro_job.id"), unique=True, index=True)
    motif: Mapped[str] = mapped_column(Text)
    statut: Mapped[StatutContestationMicroJob] = mapped_column(
        Enum(StatutContestationMicroJob), default=StatutContestationMicroJob.EN_ATTENTE
    )
    decision_motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_par_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
