from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.messagerie.models import TypeConversation


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant_id: str


class ConversationOut(BaseModel):
    """`autre_participant_*`/`classe_niveau` sont calcules par le routeur (pas des
    colonnes du modele) : l'identite de "l'autre" participant d'un DM depend de qui
    regarde, donc ne peut pas etre une simple propriete Python sur `Conversation`."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    type: TypeConversation
    classe_id: str | None
    classe_niveau: str | None = None
    autre_participant_id: str | None = None
    autre_participant_nom: str | None = None
    autre_participant_prenom: str | None = None
    created_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contenu: str = Field(min_length=1, max_length=5000)


class MessageOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    conversation_id: str
    auteur_id: str
    auteur_nom: str | None = None
    auteur_prenom: str | None = None
    contenu: str
    created_at: datetime
    est_vocal: bool = False
    duree_audio_s: int | None = None


class SignalementOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    message_id: str
    signale_par_id: str
    traite: bool
    decision: str | None
    ia_gravite: str | None = None
    ia_resume: str | None = None
    ia_decision: str | None = None


class TraiterSignalementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str


class TraiterSignalementsEnLotRequest(BaseModel):
    """`decision` absente : chaque signalement recoit la decision suggeree par l'IA (ceux
    que l'IA recommande d'examiner, ou non encore tries, sont laisses de cote)."""

    model_config = ConfigDict(extra="forbid")

    signalement_ids: list[str] = Field(min_length=1, max_length=200)
    decision: str | None = Field(default=None, max_length=500)


class ResultatLotSignalements(BaseModel):
    traites: list[str]
    ignores: list[str]
