from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.visites_virtuelles.models import TypeVisiteVirtuelle


class VisiteVirtuelleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TypeVisiteVirtuelle
    lien_externe: str
    attestation_autorisation: bool

    @field_validator("attestation_autorisation")
    @classmethod
    def _exiger_attestation(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "attestation_autorisation doit etre confirmee (autorisation de vol/droit a l'image)."
            )
        return value


class VisiteVirtuelleOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    type: TypeVisiteVirtuelle
    lien_externe: str
    attestation_autorisation: bool
