from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.evaluations.models import BaremeDevoir, StatutReferentiel, StatutSoumission


class DevoirCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str
    date_limite: datetime
    bareme: BaremeDevoir


class DevoirOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    classe_id: str
    titre: str
    date_limite: datetime
    bareme: BaremeDevoir


class SoumissionOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    devoir_id: str
    note: float | None
    statut: StatutSoumission


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: float = Field(ge=0, le=100)


class ReferentielCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niveau: str
    matiere: str
    coefficient: float = Field(gt=0)


class ReferentielPropositionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coefficient: float = Field(gt=0)


class ReferentielOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    niveau: str
    matiere: str
    coefficient: float
    statut: StatutReferentiel
    propose_pour_id: str | None


class BulletinOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_id: str
    classe_id: str
    periode: str
    moyenne_generale: float
    decision_passage: str | None
    valide_par_conseil: bool


class ValiderPassageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
