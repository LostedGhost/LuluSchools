from datetime import datetime

from pydantic import BaseModel, ConfigDict

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


class DecisionContestationMarketplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: StatutContestationMarketplace
    decision_motif: str | None = None


class ReverserVendeurRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_paiement: str
