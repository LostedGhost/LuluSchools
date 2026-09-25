from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.actes.models import StatutDemandeActe
from app.modules.paiements.schemas import AmorcerPaiementRequest  # noqa: F401 (reexporte pour compat)


class TypeActeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    prix: float = Field(ge=0, default=0)
    pieces_requises: str
    condition_eligibilite: str | None = None


class TypeActeOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    nom: str
    prix: float
    pieces_requises: str
    condition_eligibilite: str | None


class DemandeActeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type_acte_id: str | None = None
    est_reclamation: bool = False
    reference_evaluation: str | None = None
    motif: str | None = None
    eleve_utilisateur_id: str | None = None  # requis seulement quand le tuteur soumet pour son enfant

    @model_validator(mode="after")
    def _valider_exclusivite(self) -> "DemandeActeCreate":
        if self.est_reclamation and self.type_acte_id:
            raise ValueError("Une demande est soit une reclamation, soit un acte du catalogue, pas les deux.")
        if not self.est_reclamation and not self.type_acte_id:
            raise ValueError("Preciser type_acte_id ou est_reclamation.")
        if self.est_reclamation and not self.reference_evaluation:
            raise ValueError("reference_evaluation est requise pour une reclamation.")
        return self


class DemandeActeOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_id: str
    type_acte_id: str | None
    est_reclamation: bool
    statut: StatutDemandeActe
    paiement_confirme: bool
    motif_rejet: str | None


class TraiterDemandeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: StatutDemandeActe
    motif_rejet: str | None = None
