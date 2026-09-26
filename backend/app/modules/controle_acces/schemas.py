from pydantic import BaseModel, ConfigDict, model_validator

from app.modules.controle_acces.models import ServiceControle
from app.modules.identite.models import RoleUtilisateur


class DesignationControleurCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utilisateur_id: str
    service: ServiceControle
    evenement_id: str | None = None

    @model_validator(mode="after")
    def _valider_evenement_id(self) -> "DesignationControleurCreate":
        if self.service == ServiceControle.EVENEMENT and not self.evenement_id:
            raise ValueError("evenement_id est requis pour une designation de service 'evenement'.")
        if self.service != ServiceControle.EVENEMENT and self.evenement_id:
            raise ValueError("evenement_id ne s'applique qu'a une designation de service 'evenement'.")
        return self


class DesignationControleurOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    utilisateur_id: str
    service: ServiceControle
    evenement_id: str | None


class UtilisateurDesignableOut(BaseModel):
    """UC-28 : recherche par nom pour la designation de controleur, meme pattern que
    EnseignantSigneOut (recrutement) pour l'affectation enseignant<->classe - remplace la
    saisie d'un id brut (limite connue documentee dans PROJECT_MAP)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nom: str
    prenom: str
    email: str | None
    role: RoleUtilisateur
