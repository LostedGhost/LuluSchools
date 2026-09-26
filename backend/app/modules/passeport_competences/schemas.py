from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuizReussiOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quiz_id: str
    cours_titre: str
    cours_chapitre: str
    score: float
    date: datetime


class CoursSuiviOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    titre: str
    chapitre: str
    format: str


class MoyenneMatiereOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matiere: str
    moyenne: float


class BadgeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class PasseportOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_utilisateur_id: str
    eleve_nom: str
    eleve_prenom: str
    quiz_reussis: list[QuizReussiOut]
    cours_suivis: list[CoursSuiviOut]
    moyennes_par_matiere: list[MoyenneMatiereOut]
    badges: list[BadgeOut]


class PasseportExportOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lulufiles_file_id: str
    lien: str
