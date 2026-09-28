"""Registre des documents papier saisis par l'administration (« guichet papier »).

Pour les personnes sans smartphone (enseignant, élève, parent), l'administration
photographie le document papier ; l'IA le lit, l'administrateur vérifie et valide. Chaque
saisie garde ici la photo (preuve), ce que l'IA a lu, qui a validé, quand, et l'objet créé
(devoir, cours, inscription, contrat...).
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TypeDocumentPapier(str, enum.Enum):
    FEUILLE_NOTES = "feuille_notes"
    FEUILLE_APPEL = "feuille_appel"
    COURS = "cours"
    FICHE_INSCRIPTION = "fiche_inscription"
    COPIE = "copie"
    CONTRAT_SIGNE = "contrat_signe"
    CONSENTEMENT = "consentement"


class StatutDocumentPapier(str, enum.Enum):
    LU = "lu"  # lu par l'IA, en attente de validation humaine
    ENREGISTRE = "enregistre"  # valide : l'objet est cree


class DocumentPapier(Base):
    __tablename__ = "documents_papier"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    type: Mapped[TypeDocumentPapier] = mapped_column(Enum(TypeDocumentPapier))
    statut: Mapped[StatutDocumentPapier] = mapped_column(Enum(StatutDocumentPapier), default=StatutDocumentPapier.LU)
    # Photos / scans (une ou plusieurs pages), stockes dans LuluFiles.
    fichiers: Mapped[list] = mapped_column(JSON, default=list)
    # Ce que l'IA a lu (brut), puis ce qui a ete enregistre apres verification humaine.
    lecture_ia: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    donnees_enregistrees: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    objet_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    objet_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    saisi_par_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    enregistre_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
