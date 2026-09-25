from pydantic import BaseModel, ConfigDict, model_validator

from app.modules.controle_acces.models import ServiceControle


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
