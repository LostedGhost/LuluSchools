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
    nombre_questions: int = Field(default=5, ge=1, le=20)


class QuestionQuizPubliqueOut(BaseModel):
    """Ne jamais exposer reponse_correcte_index a l'eleve avant sa tentative."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    ordre: int
    enonce: str
    choix: list[str]


class QuizOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    cours_id: str
    seuil_reussite: float
    questions: list[QuestionQuizPubliqueOut]


class TentativeQuizCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reponses: list[int]


class TentativeQuizOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    score: float
    reussie: bool
