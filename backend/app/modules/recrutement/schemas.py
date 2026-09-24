from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.recrutement.models import (
    StatutCandidature,
    StatutContestation,
    StatutContrat,
    StatutDocument,
    StatutPoste,
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

    type_document: str
    note_ia: float | None
    statut: StatutDocument


class CandidatureOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    poste_id: str
    statut: StatutCandidature
    score: float | None
    documents: list[DocumentCandidatureOut]


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


class ContratOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    candidature_id: str
    syllabus: str
    statut: StatutContrat
    signature_horodatage: datetime | None


class ContratSignerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom_tape: str
