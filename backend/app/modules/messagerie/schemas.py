from datetime import datetime

from pydantic import BaseModel, ConfigDict

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

    contenu: str


class MessageOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    conversation_id: str
    auteur_id: str
    auteur_nom: str | None = None
    auteur_prenom: str | None = None
    contenu: str
    created_at: datetime


class SignalementOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    message_id: str
    signale_par_id: str
    traite: bool
    decision: str | None


class TraiterSignalementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
