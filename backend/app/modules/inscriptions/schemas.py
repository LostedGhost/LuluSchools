from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.inscriptions.models import StatutInscription


class InscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    prenom: str
    date_naissance: date
    classe_id: str
    consentement_parental_donne: bool = False


class InscriptionOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_id: str
    classe_id: str
    statut: StatutInscription
    consentement_parental_horodatage: datetime | None = None
    motif_rejet: str | None = None


class RejetInscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str
