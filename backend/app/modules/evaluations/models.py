import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaremeDevoir(str, enum.Enum):
    RIGIDE = "rigide"
    FLEXIBLE = "flexible"


class StatutSoumission(str, enum.Enum):
    EN_CORRECTION = "en_correction"
    CORRIGEE = "corrigee"
    ECHEC_CORRECTION = "echec_correction"


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
    matiere: Mapped[str] = mapped_column(String(100))
    date_limite: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bareme: Mapped[BaremeDevoir] = mapped_column(Enum(BaremeDevoir))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    questions: Mapped[list["QuestionDevoir"]] = relationship(back_populates="devoir")


class QuestionDevoir(Base):
    """Un devoir est un formulaire (UC-08) : chaque question porte son propre bareme de
    correction (texte libre instructant le LLM) et son nombre de points maximum."""

    __tablename__ = "questions_devoir"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    devoir_id: Mapped[str] = mapped_column(ForeignKey("devoirs.id"), index=True)
    ordre: Mapped[int] = mapped_column(Integer)
    enonce: Mapped[str] = mapped_column(Text)
    bareme_reponse: Mapped[str] = mapped_column(Text)
    points_max: Mapped[float] = mapped_column(Float)

    devoir: Mapped[Devoir] = relationship(back_populates="questions")


class Soumission(Base):
    """Pas de ligne = pas de soumission = compte pour 0 au calcul de la moyenne (UC-08 :
    absence de soumission a l'echeance = note zero automatique, sans derogation) - pas
    besoin d'un job planifie pour materialiser ce zero, il est calcule a la volee. La
    correction est automatique (LLM, selon le bareme de chaque question) et EXECUTEE EN
    ARRIERE-PLAN (BackgroundTasks) apres la reponse HTTP de soumission : FreeLLM n'a
    aucun SLA (ADR-002) et une correction porte sur N questions (N appels), donc
    potentiellement plusieurs secondes - ne doit jamais bloquer la requete de l'eleve.
    statut=en_correction tant que le traitement n'est pas termine, puis corrigee ou
    echec_correction (en cas d'echec, la soumission attend une revision manuelle via
    POST /soumissions/{id}/corriger)."""

    __tablename__ = "soumissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    devoir_id: Mapped[str] = mapped_column(ForeignKey("devoirs.id"), index=True)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    note: Mapped[float | None] = mapped_column(Float, nullable=True)
    statut: Mapped[StatutSoumission] = mapped_column(Enum(StatutSoumission))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    reponses: Mapped[list["ReponseSoumission"]] = relationship(back_populates="soumission")


class ReponseSoumission(Base):
    __tablename__ = "reponses_soumission"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    soumission_id: Mapped[str] = mapped_column(ForeignKey("soumissions.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions_devoir.id"), index=True)
    texte_reponse: Mapped[str] = mapped_column(Text)
    points_obtenus: Mapped[float | None] = mapped_column(Float, nullable=True)
    commentaire_ia: Mapped[str | None] = mapped_column(Text, nullable=True)

    soumission: Mapped[Soumission] = relationship(back_populates="reponses")


class ReferentielCoefficient(Base):
    """UC-09 : fixe par le ministere (A++), l'etablissement (A+) peut proposer une mise a
    jour, effective seulement apres validation ministerielle. Utilise pour ponderer la
    moyenne du bulletin par (classe.niveau, devoir.matiere) - voir
    evaluations.router._calculer_et_enregistrer_bulletin."""

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
