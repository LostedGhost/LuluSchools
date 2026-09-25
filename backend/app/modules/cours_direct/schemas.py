from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.cours_direct.models import StatutSessionLive


class SessionLiveCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_heure: datetime


class SessionLiveOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    classe_id: str
    enseignant_id: str
    date_heure: datetime
    statut: StatutSessionLive


class SessionLiveDemarreeOut(SessionLiveOut):
    token_connexion: str


class ConsentementCameraLiveOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    eleve_utilisateur_id: str
    date_consentement: datetime


class ParticipationLiveOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    eleve_utilisateur_id: str
    camera_autorisee: bool
    token_connexion: str
