"""Lot 7.8 — EFTP et insertion (PAG 2021-2026, axe 5, action 2 ; « programme de stages au
profit des jeunes », « projet d'inclusion des jeunes »)."""

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OffreStage(Base):
    """Offre d'une entreprise partenaire, publiee par l'etablissement (A+) pour ses propres
    eleves/etudiants : l'entreprise n'a pas besoin de compte sur la plateforme."""

    __tablename__ = "offres_stage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    entreprise: Mapped[str] = mapped_column(String(200))
    intitule: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    lieu: Mapped[str] = mapped_column(String(120))
    filiere: Mapped[str | None] = mapped_column(String(100), nullable=True)  # None = toutes
    duree_semaines: Mapped[int] = mapped_column(Integer)
    date_limite: Mapped[date] = mapped_column(Date)
    contact: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    publie_par_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class StatutCandidatureStage(str, enum.Enum):
    ENVOYEE = "envoyee"
    RETENUE = "retenue"
    NON_RETENUE = "non_retenue"


class CandidatureStage(Base):
    __tablename__ = "candidatures_stage"
    __table_args__ = (UniqueConstraint("offre_id", "eleve_utilisateur_id", name="uq_candidature_stage"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    offre_id: Mapped[str] = mapped_column(ForeignKey("offres_stage.id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    statut: Mapped[StatutCandidatureStage] = mapped_column(
        Enum(StatutCandidatureStage, name="statutcandidaturestage"), default=StatutCandidatureStage.ENVOYEE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class NiveauCompetence(str, enum.Enum):
    INITIE = "initie"
    CONFIRME = "confirme"
    MAITRISE = "maitrise"


class CompetenceMetier(Base):
    """Competence professionnelle validee par un enseignant de l'eleve (passeport de
    competences) : ce que l'eleve SAIT FAIRE, pas seulement ses notes."""

    __tablename__ = "competences_metier"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    intitule: Mapped[str] = mapped_column(String(200))
    niveau: Mapped[NiveauCompetence] = mapped_column(Enum(NiveauCompetence, name="niveaucompetence"))
    valide_par_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
