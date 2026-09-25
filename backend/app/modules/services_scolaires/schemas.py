from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.modules.services_scolaires.models import StatutTicket


class LigneTransportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    prix: float = Field(ge=0)
    capacite_par_trajet: int = Field(gt=0)


class LigneTransportOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    nom: str
    prix: float
    capacite_par_trajet: int


class TicketTransportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_trajet: date
    eleve_utilisateur_id: str | None = None  # requis seulement quand le tuteur achete pour son enfant


class TicketTransportOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    ligne_id: str
    utilisateur_id: str
    date_trajet: date
    statut: StatutTicket
    prix_paye: float
    paiement_confirme: bool


class TypeRepasCantineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    prix: float = Field(ge=0)
    capacite_par_jour: int = Field(gt=0)


class TypeRepasCantineOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    nom: str
    prix: float
    capacite_par_jour: int


class TicketCantineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_service: date
    eleve_utilisateur_id: str | None = None


class TicketCantineOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    type_repas_id: str
    utilisateur_id: str
    date_service: date
    statut: StatutTicket
    prix_paye: float
    paiement_confirme: bool
