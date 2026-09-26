from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.micro_jobs.models import StatutContestationMicroJob, StatutMissionMicroJob, StatutOffreMicroJob


class OffreMicroJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str
    description: str
    prix: float = Field(gt=0)


class OffreMicroJobOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    client_id: str
    titre: str
    description: str
    prix: float
    statut: StatutOffreMicroJob
    paiement_confirme: bool


class MissionMicroJobOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    offre_id: str
    prestataire_id: str
    statut: StatutMissionMicroJob
    prix_paye: float
    paiement_confirme: bool
    date_declaration_fin: datetime | None
    date_limite_validation: datetime | None
    reference_paiement_prestataire: str | None


class ContesterMissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str


class DecisionContestationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: StatutContestationMicroJob
    decision_motif: str | None = None


class ContestationMicroJobOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    mission_id: str
    motif: str
    statut: StatutContestationMicroJob
    decision_motif: str | None


class ReverserPrestataireRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_paiement: str
