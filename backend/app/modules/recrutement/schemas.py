from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.recrutement.models import (
    StatutCandidature,
    StatutContestation,
    StatutContrat,
    StatutDocument,
    StatutPoste,
    StatutProposition,
)


class CritereDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type_document: str
    coefficient: float = Field(gt=0)
    seuil_minimal: float = Field(ge=0, le=100)


class PosteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str
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
    documents: list[DocumentCandidatureOut]
    enseignant_nom: str
    enseignant_prenom: str


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
