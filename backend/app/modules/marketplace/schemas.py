from datetime import datetime

from pydantic import Field, BaseModel, ConfigDict

from app.modules.marketplace.models import (
    CategorieAnnonce,
    EtatArticle,
    StatutAnnonce,
    StatutContestationMarketplace,
    StatutTransactionMarketplace,
)


class AnnonceMarketplaceOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    vendeur_id: str
    titre: str
    description: str
    categorie: CategorieAnnonce
    etat: EtatArticle
    prix: float
    statut: StatutAnnonce


class PhotoAnnonceLienOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    url: str
    ordre: int


class AnnonceMarketplaceDetailOut(AnnonceMarketplaceOut):
    photos: list[PhotoAnnonceLienOut] = []


class AnnoncesMarketplacePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AnnonceMarketplaceOut]
    total: int
    page: int
    page_size: int


class RetirerAnnonceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str


class SignalementAnnonceOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    annonce_id: str
    signale_par_id: str
    traite: bool
    decision: str | None
    ia_gravite: str | None = None
    ia_resume: str | None = None
    ia_decision: str | None = None


class TraiterSignalementAnnonceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str


class TransactionMarketplaceOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    annonce_id: str
    acheteur_id: str
    statut: StatutTransactionMarketplace
    prix_paye: float
    paiement_confirme: bool
    date_remise_declaree: datetime | None
    date_limite_confirmation: datetime | None
    reference_paiement_vendeur: str | None


class ContesterTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str


class ContestationMarketplaceOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    transaction_id: str
    motif: str
    statut: StatutContestationMarketplace
    decision_motif: str | None
    ia_decision: str | None = None
    ia_justification: str | None = None


class ContestationMarketplaceAEtrancherOut(ContestationMarketplaceOut):
    """Vue enrichie utilisee uniquement par la liste d'arbitrage (GET .../contestations-en-
    attente) - meme raisonnement que ContestationMicroJobAEtrancherOut : sans elle, l'admin
    n'a aucun moyen de decouvrir quelles contestations existent."""

    created_at: datetime
    annonce_titre: str
    prix_paye: float


class DecisionContestationMarketplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: StatutContestationMarketplace
    decision_motif: str | None = None


class ReverserVendeurRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_paiement: str


class TransactionAReverserOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    annonce_titre: str
    prix_paye: float
    vendeur_id: str = ""
    vendeur_nom: str
    vendeur_prenom: str
    vendeur_telephone: str | None
    date_remise_declaree: datetime | None


class ReversementEnLotRequest(BaseModel):
    """Un virement Mobile Money unique pour plusieurs ventes/missions du MEME beneficiaire :
    une seule reference pour tout le lot."""

    model_config = ConfigDict(extra="forbid")

    ids: list[str] = Field(min_length=1, max_length=200)
    reference_paiement: str = Field(min_length=3, max_length=100)


class ResultatReversementEnLot(BaseModel):
    reverses: list[str]
    montant_total: float
