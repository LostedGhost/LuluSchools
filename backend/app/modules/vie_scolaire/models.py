import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aujourdhui() -> date:
    return datetime.now(timezone.utc).date()


class NatureEntreeVieScolaire(str, enum.Enum):
    ABSENCE = "absence"
    RETARD = "retard"
    APPRECIATION = "appreciation"
    INCIDENT = "incident"
    FELICITATION = "felicitation"


class EntreeVieScolaire(Base):
    """UC-23 : historique immuable (jamais de PATCH/DELETE - meme logique que la
    messagerie, Art. 519/521/550, sur des donnees concernant potentiellement des
    mineurs). `matiere` est None uniquement pour une entree globale, reservee au
    professeur principal de la classe (AffectationEnseignant.est_professeur_principal)
    ou a un admin - un enseignant de matiere ordinaire doit toujours preciser la sienne.
    La portee de lecture reproduit cette meme distinction : un enseignant ordinaire ne
    voit QUE ses propres entrees (auteur_id == lui), le professeur principal et l'admin
    voient tout - voir vie_scolaire/router.py::_verifier_lecture_vie_scolaire."""

    __tablename__ = "entrees_vie_scolaire"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    auteur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    nature: Mapped[NatureEntreeVieScolaire] = mapped_column(Enum(NatureEntreeVieScolaire))
    matiere: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    date_survenue: Mapped[date] = mapped_column(Date, default=_aujourdhui)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
