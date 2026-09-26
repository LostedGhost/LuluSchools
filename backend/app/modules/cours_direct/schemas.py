from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.cours_direct.models import (
    ModePermissionEcriture,
    StatutDemandeCraie,
    StatutSessionLive,
    TypeTraitTableau,
)


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


class PanneauTableauOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    ordre: int


class TraitTableauCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TypeTraitTableau
    donnees: dict[str, Any] = Field(default_factory=dict)


class TraitTableauOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    panneau_id: str
    auteur_id: str
    type: TypeTraitTableau
    donnees: dict[str, Any]
    created_at: datetime


class PanneauAvecTraitsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    panneau: PanneauTableauOut
    traits: list[TraitTableauOut]


class PermissionEcritureOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    eleve_utilisateur_id: str
    mode: ModePermissionEcriture


class DemandeCraieOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    eleve_utilisateur_id: str
    statut: StatutDemandeCraie


class EtatTableauOut(BaseModel):
    """Etat complet du tableau d'une session - un seul appel pour un client qui rejoint
    en cours de route (ou pour un simple polling de secours en tres faible connectivite,
    sans passer par le canal temps reel)."""

    model_config = ConfigDict(extra="forbid")

    panneaux: list[PanneauAvecTraitsOut]
    permissions: list[PermissionEcritureOut]
    demandes_en_attente: list[DemandeCraieOut] = Field(default_factory=list)  # vide pour un eleve


class PermissionEcritureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eleve_utilisateur_id: str


class CaptureTableauOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    panneau_id: str
    lulufiles_file_id: str
    created_at: datetime


class MessageSessionLiveCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contenu: str


class MessageSessionLiveOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    auteur_id: str
    contenu: str
    created_at: datetime


class ResumeSessionLiveOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    contenu: str
    created_at: datetime
