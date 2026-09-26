from datetime import date

from pydantic import BaseModel, ConfigDict


class RadarFamilialOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_utilisateur_id: str
    periode_debut: date
    periode_fin: date
    resume: str
    sources: list[str]
