from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.actes.models import StatutDemandeActe
from app.modules.paiements.schemas import AmorcerPaiementRequest  # noqa: F401 (reexporte pour compat)
from app.modules.recrutement.schemas import ChampFormulaire


class TypeActeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    prix: float = Field(ge=0, default=0)
    pieces_requises: str
    condition_eligibilite: str | None = None
    schema_formulaire: list[ChampFormulaire] | None = None
    # Genere et livre automatiquement des le paiement ; None = traitement manuel.
    modele_document: Literal["attestation_scolarite", "releve_notes", "certificat_reussite"] | None = None


class TypeActeOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    nom: str
    prix: float
    pieces_requises: str
    condition_eligibilite: str | None
    schema_formulaire: list[ChampFormulaire] | None
    modele_document: str | None = None


class DemandeActeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type_acte_id: str | None = None
    est_reclamation: bool = False
    reference_evaluation: str | None = None
    motif: str | None = None
    eleve_utilisateur_id: str | None = None  # requis seulement quand le tuteur soumet pour son enfant
    reponses_formulaire: dict | None = None  # UC-51/65 : champs non-fichier uniquement, voir POST .../pieces/{champ_id}

    @model_validator(mode="after")
    def _valider_exclusivite(self) -> "DemandeActeCreate":
        if self.est_reclamation and self.type_acte_id:
            raise ValueError("Une demande est soit une réclamation, soit un acte du catalogue, pas les deux.")
        if not self.est_reclamation and not self.type_acte_id:
            raise ValueError("Choisissez un acte du catalogue ou une réclamation de note.")
        if self.est_reclamation and not self.reference_evaluation:
            raise ValueError("Indiquez le devoir concerné par la réclamation.")
        return self


class DemandeActeOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_id: str
    eleve_nom: str
    eleve_prenom: str
    eleve_matricule: str | None
    type_acte_id: str | None
    est_reclamation: bool
    reponses_formulaire: dict | None
    document_final_lulufiles_id: str | None
    statut: StatutDemandeActe
    paiement_confirme: bool
    motif_rejet: str | None
    analyse_ia: str | None = None


class TraiterDemandeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: StatutDemandeActe
    motif_rejet: str | None = None


class LienDocumentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
