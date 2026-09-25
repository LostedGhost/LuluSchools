from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.evaluations.models import BaremeDevoir, StatutReferentiel, StatutSoumission


class QuestionDevoirCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enonce: str
    bareme_reponse: str
    points_max: float = Field(gt=0)


class QuestionDevoirOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    ordre: int
    enonce: str
    points_max: float


class QuestionDevoirAvecBaremeOut(BaseModel):
    """Reservee a l'enseignant proprietaire du devoir (ecran de revision manuelle) -
    jamais exposee sur DevoirOut/QuestionDevoirOut, qui sont aussi lus par l'eleve avant
    qu'il ait repondu (GET /devoirs/{id} et GET /classes/{id}/devoirs sont ouverts a
    ELEVE) : y ajouter bareme_reponse revelerait la reponse attendue avant soumission."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    ordre: int
    enonce: str
    bareme_reponse: str
    points_max: float


class DevoirCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str
    matiere: str
    date_limite: datetime
    bareme: BaremeDevoir
    questions: list[QuestionDevoirCreate] = Field(min_length=1)


class DevoirOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    classe_id: str
    titre: str
    matiere: str
    date_limite: datetime
    bareme: BaremeDevoir
    questions: list[QuestionDevoirOut]


class ReponseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    texte_reponse: str


class SoumissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reponses: list[ReponseCreate] = Field(min_length=1)


class ReponseOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    question_id: str
    texte_reponse: str
    points_obtenus: float | None


class SoumissionOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    devoir_id: str
    note: float | None
    statut: StatutSoumission
    reponses: list[ReponseOut]


class CorrectionManuelleReponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    points_obtenus: float = Field(ge=0)


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reponses: list[CorrectionManuelleReponse] = Field(min_length=1)


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
