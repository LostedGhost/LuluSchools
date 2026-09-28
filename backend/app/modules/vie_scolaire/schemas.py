from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.modules.vie_scolaire.models import NatureEntreeVieScolaire


class EntreeVieScolaireCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nature: NatureEntreeVieScolaire
    matiere: str | None = None
    description: str
    date_survenue: date | None = None

    @model_validator(mode="after")
    def _valider_coherence(self) -> "EntreeVieScolaireCreate":
        if not self.description.strip():
            raise ValueError("La description ne peut pas être vide.")
        if self.matiere is not None and not self.matiere.strip():
            raise ValueError("Choisissez une matière, ou aucune pour une entrée globale.")
        return self


class EntreeVieScolaireOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_id: str
    classe_id: str
    auteur_id: str
    nature: NatureEntreeVieScolaire
    matiere: str | None
    description: str
    date_survenue: date
    created_at: datetime
