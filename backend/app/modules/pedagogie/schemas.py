from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.pedagogie.models import (
    FormatCours,
    OrigineAlerteElProfessor,
    RoleMessageElProfessor,
    RoleMessageElProfessorEnseignant,
    RoleMessageElProfessorFamille,
    RoleMessageElProfessorTuteur,
)


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
    contenu_texte: str | None
    lulufiles_file_id: str | None


class LienFichierOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


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


class MessageElProfessorOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    role: RoleMessageElProfessor
    contenu: str
    created_at: datetime


class SessionElProfessorOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_utilisateur_id: str
    cours_id: str
    messages: list[MessageElProfessorOut]


class QuestionElProfessorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)


class MasquerContenuRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str = Field(min_length=1)


class AdminCoursOut(BaseModel):
    """UC-37/53 (lot admin ministeriel) : vue agregee tous etablissements, avec les noms
    denormalises (meme raisonnement que CandidatureOut.enseignant_nom en Phase 1 - un
    cours anonyme par ses seuls id serait inutilisable pour une supervision nationale)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    titre: str
    chapitre: str
    format: FormatCours
    classe_id: str
    etablissement_id: str
    etablissement_nom: str
    enseignant_id: str
    enseignant_nom: str
    enseignant_prenom: str
    masque: bool
    created_at: datetime


class AdminCoursPageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminCoursOut]
    total: int
    limit: int
    offset: int


class SessionElProfessorEnseignantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_utilisateur_id: str | None = None
    sujet: str | None = None


class MessageElProfessorEnseignantOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    role: RoleMessageElProfessorEnseignant
    contenu: str
    created_at: datetime


class SessionElProfessorEnseignantOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    enseignant_id: str
    eleve_utilisateur_id: str | None
    sujet: str | None
    messages: list[MessageElProfessorEnseignantOut]


class AlerteElProfessorOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    origine: OrigineAlerteElProfessor
    session_id: str
    etablissement_id: str | None
    eleve_utilisateur_id: str | None
    motif: str
    traite: bool
    created_at: datetime


class SessionElProfessorTuteurCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_utilisateur_id: str
    sujet: str | None = None


class MessageElProfessorTuteurOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    role: RoleMessageElProfessorTuteur
    contenu: str
    created_at: datetime


class SessionElProfessorTuteurOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    tuteur_id: str
    eleve_utilisateur_id: str
    sujet: str | None
    messages: list[MessageElProfessorTuteurOut]


class SessionElProfessorFamilleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_utilisateur_id: str
    sujet: str | None = None


class MessageElProfessorFamilleOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    role: RoleMessageElProfessorFamille
    contenu: str
    created_at: datetime


class SessionElProfessorFamilleOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    tuteur_id: str
    eleve_utilisateur_id: str
    sujet: str | None
    rejointe_le: datetime | None
    messages: list[MessageElProfessorFamilleOut]
