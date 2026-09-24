import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaremeDevoir(str, enum.Enum):
    RIGIDE = "rigide"
    FLEXIBLE = "flexible"


class StatutSoumission(str, enum.Enum):
    A_TEMPS = "a_temps"
    CORRIGEE = "corrigee"


class StatutReferentiel(str, enum.Enum):
    VALIDE = "valide"
    PROPOSITION_EN_ATTENTE = "proposition_en_attente"
    REMPLACE = "remplace"


class Devoir(Base):
    __tablename__ = "devoirs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignants.utilisateur_id"), index=True)
    titre: Mapped[str] = mapped_column(String(200))
    date_limite: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bareme: Mapped[BaremeDevoir] = mapped_column(Enum(BaremeDevoir))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Soumission(Base):
    """Pas de ligne = pas de soumission = compte pour 0 au calcul de la moyenne (UC-08 :
    absence de soumission a l'echeance = note zero automatique, sans derogation) - pas
    besoin d'un job planifie pour materialiser ce zero, il est calcule a la volee."""

    __tablename__ = "soumissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    devoir_id: Mapped[str] = mapped_column(ForeignKey("devoirs.id"), index=True)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    lulufiles_file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note: Mapped[float | None] = mapped_column(Float, nullable=True)
    statut: Mapped[StatutSoumission] = mapped_column(Enum(StatutSoumission), default=StatutSoumission.A_TEMPS)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ReferentielCoefficient(Base):
    """UC-09 : fixe par le ministere (A++), l'etablissement (A+) peut proposer une mise a
    jour, effective seulement apres validation ministerielle. Pas encore branche sur le
    calcul du bulletin (moyenne simple pour l'instant, voir Bulletin) - gouvernance posee
    independamment du calcul, a relier plus tard."""

    __tablename__ = "referentiels_coefficients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    niveau: Mapped[str] = mapped_column(String(100))
    matiere: Mapped[str] = mapped_column(String(100))
    coefficient: Mapped[float] = mapped_column(Float)
    statut: Mapped[StatutReferentiel] = mapped_column(Enum(StatutReferentiel))
    etablissement_proposant_id: Mapped[str | None] = mapped_column(
        ForeignKey("etablissements.id"), nullable=True
    )
    propose_pour_id: Mapped[str | None] = mapped_column(
        ForeignKey("referentiels_coefficients.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Bulletin(Base):
    __tablename__ = "bulletins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    periode: Mapped[str] = mapped_column(String(50))
    moyenne_generale: Mapped[float] = mapped_column(Float)
    decision_passage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    valide_par_conseil: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
