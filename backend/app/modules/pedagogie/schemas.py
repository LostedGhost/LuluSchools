from pydantic import BaseModel, ConfigDict, Field

from app.modules.pedagogie.models import FormatCours


class CoursCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str
    chapitre: str
    format: FormatCours
    contenu_texte: str | None = None


class CoursOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    classe_id: str
    titre: str
    chapitre: str
    format: FormatCours
    lulufiles_file_id: str | None


class QuizCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seuil_reussite: float = Field(default=80.0, ge=0, le=100)


class QuizOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    cours_id: str
    seuil_reussite: float


class TentativeQuizCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0, le=100)


class TentativeQuizOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    score: float
    reussie: bool
