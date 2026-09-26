from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.coffre_fort.models import ModuleDepenseCoffreFort, StatutValidationParentale


class PlafondFamilialUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plafond_hebdomadaire: float | None = None
    seuil_validation: float | None = None


class PlafondFamilialOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_utilisateur_id: str
    plafond_hebdomadaire: float | None
    seuil_validation: float | None
    updated_at: datetime


class ValidationParentaleOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_utilisateur_id: str
    module: ModuleDepenseCoffreFort
    reference_id: str
    montant: float
    statut: StatutValidationParentale
    motif_refus: str | None
    decidee_at: datetime | None
    created_at: datetime


class DecisionValidationParentaleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif_refus: str | None = None


class AlerteDepassementPlafondOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_utilisateur_id: str
    module: ModuleDepenseCoffreFort
    montant_semaine: float
    plafond: float
    created_at: datetime


class ReleveFinancierOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_utilisateur_id: str
    periode_debut: date | None
    periode_fin: date | None
    gains_micro_jobs: float
    ventes_marketplace: float
    achats_marketplace: float
    depenses_micro_jobs: float
    frais_actes: float
    solde_net: float
