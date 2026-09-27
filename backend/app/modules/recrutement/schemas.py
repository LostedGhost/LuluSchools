from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.recrutement.models import (
    StatutCandidature,
    StatutContestation,
    StatutContrat,
    StatutDocument,
    StatutPoste,
    StatutProposition,
    StatutVerificationCasier,
)

TypeChampFormulaire = Literal["texte_court", "texte_long", "fichier", "choix_unique", "choix_multiple"]


class ChampFormulaire(BaseModel):
    """UC-47/50/62/64 (lot admin etablissement) : un seul moteur de formulaire dynamique,
    partage entre Poste (recrutement) et TypeActeAcademique (actes academiques) - pattern
    JSON-schema-driven standard (type/label/requis/options par champ)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=200)
    type: TypeChampFormulaire
    requis: bool = False
    options: list[str] | None = None


class CritereDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type_document: str
    coefficient: float = Field(gt=0)
    seuil_minimal: float = Field(ge=0, le=100)


class PosteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str
    description: str | None = None
    matiere: str | None = None
    remuneration_min: float | None = Field(default=None, ge=0)
    remuneration_max: float | None = Field(default=None, ge=0)
    schema_formulaire: list[ChampFormulaire] | None = None
    criteres: list[CritereDocumentCreate]


class CritereDocumentOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    type_document: str
    coefficient: float
    seuil_minimal: float


class PosteOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    titre: str
    description: str | None
    matiere: str | None
    remuneration_min: float | None
    remuneration_max: float | None
    schema_formulaire: list[ChampFormulaire] | None
    statut: StatutPoste
    criteres: list[CritereDocumentOut]


class DocumentCandidatureOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    type_document: str
    note_ia: float | None
    statut: StatutDocument
    lulufiles_file_id: str | None


class LienFichierOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


class CandidatureOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    poste_id: str
    statut: StatutCandidature
    score: float | None
    reponses_formulaire: dict | None
    documents: list[DocumentCandidatureOut]
    enseignant_nom: str
    enseignant_prenom: str
    statut_casier_judiciaire: StatutVerificationCasier | None = None


class VerificationCasierOut(BaseModel):
    """Jamais le contenu du casier lui-meme (telechargement dedie, reserve a l'A+
    recruteur) : seulement le statut et les dates de verification/purge."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    candidature_id: str
    statut: StatutVerificationCasier
    date_verification: datetime | None
    date_suppression_prevue: datetime | None
    document_disponible: bool


class VerdictCasierRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conforme: bool


class EnseignantSigneOut(BaseModel):
    """Utilise pour la recherche par nom lors d'une affectation enseignant<->classe
    (voir etablissements/router.py::AffectationEnseignant) - expose volontairement le
    nom/prenom en plus de l'id, contrairement a CandidatureOut qui ne renvoie que l'id
    de la candidature (jamais celui de l'enseignant)."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    prenom: str
    email: str | None


class ContestationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str


class ContestationOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    candidature_id: str
    motif: str
    statut: StatutContestation
    motif_decision: str | None


class ContestationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: StatutContestation
    motif_decision: str | None = None


class ContratCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    syllabus: str
    date_fin: date


class ContratOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    candidature_id: str
    etablissement_id: str
    syllabus: str
    date_fin: date
    statut: StatutContrat
    signature_horodatage: datetime | None
    signature_image_lulufiles_id: str | None


class ContratAvecEnseignantOut(ContratOut):
    """Utilise pour la liste des contrats d'un etablissement cote admin (UC-05b) -
    expose le nom/prenom de l'enseignant en plus des champs de ContratOut, sur le
    meme principe que EnseignantSigneOut."""

    enseignant_nom: str
    enseignant_prenom: str


class ReconductionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    syllabus: str
    date_fin: date


class NotationManuelleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: float = Field(ge=0, le=100)


class PropositionReconductionOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    contrat_precedent_id: str
    nouveau_contrat_id: str | None
    statut: StatutProposition
