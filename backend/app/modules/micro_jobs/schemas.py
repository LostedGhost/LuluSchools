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


class ContestationMicroJobDetailOut(BaseModel):
    """UC-31/32/46/47 (lot admin ministeriel) : version enrichie de ContestationMicroJobOut
    pour la file d'arbitrage - contexte complet (mission, offre, parties) avant decision,
    plutot que la saisie d'un id a l'aveugle (meme constat que la file d'arbitrage
    gig-economy etudiee dans le cahier des charges)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    mission_id: str
    motif: str
    statut: StatutContestationMicroJob
    decision_motif: str | None
    created_at: datetime
    offre_titre: str
    prix: float
    client_nom: str
    client_prenom: str
    prestataire_nom: str
    prestataire_prenom: str


class MissionAReverserOut(BaseModel):
    """UC-33/48 : file des missions validees en attente de reversement, avec le contact du
    prestataire deja connu (telephone) plutot qu'une reference a ressaisir manuellement."""

    model_config = ConfigDict(extra="forbid")

    id: str
    offre_titre: str
    prix_paye: float
    prestataire_id: str
    prestataire_nom: str
    prestataire_prenom: str
    prestataire_telephone: str | None
    date_declaration_fin: datetime | None
