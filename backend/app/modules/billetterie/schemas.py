from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.billetterie.models import StatutBillet, StatutEvenement


class EvenementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str
    description: str
    lieu: str
    date_heure: datetime
    capacite_max: int = Field(gt=0)
    prix_billet: float = Field(ge=0, default=0)


class EvenementOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    titre: str
    description: str
    lieu: str
    date_heure: datetime
    capacite_max: int
    prix_billet: float
    statut: StatutEvenement
    parrain_utilisateur_id: str | None


class DesignerParrainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utilisateur_id: str


class BilletAchatRequest(BaseModel):
    """UC-29.1 : optionnel - permet a un tuteur d'acheter un billet POUR SON ENFANT
    (beneficiaire distinct de l'acheteur), meme pattern que
    services_scolaires.TicketTransportCreate/TicketCantineCreate. Omis, le billet reste
    attribue a l'appelant lui-meme (comportement inchange pour un achat pour soi)."""

    model_config = ConfigDict(extra="forbid")

    eleve_utilisateur_id: str | None = None


class BilletEvenementOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    evenement_id: str
    utilisateur_id: str
    statut: StatutBillet
    prix_paye: float
    paiement_confirme: bool
