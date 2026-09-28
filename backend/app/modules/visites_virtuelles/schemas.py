from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.visites_virtuelles.models import TypeVisiteVirtuelle


class VisiteVirtuelleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TypeVisiteVirtuelle
    lien_externe: str = Field(max_length=2000)
    attestation_autorisation: bool

    @field_validator("lien_externe")
    @classmethod
    def _exiger_https(cls, value: str) -> str:
        # Affiche comme lien cliquable : jamais de schema javascript:/data: (XSS stocke).
        if not value.strip().lower().startswith("https://"):
            raise ValueError("Le lien doit commencer par https://")
        return value.strip()

    @field_validator("attestation_autorisation")
    @classmethod
    def _exiger_attestation(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "Cochez l'attestation d'autorisation de vol et de droit à l'image."
            )
        return value


class VisiteVirtuelleOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    etablissement_id: str
    type: TypeVisiteVirtuelle
    lien_externe: str
    attestation_autorisation: bool
