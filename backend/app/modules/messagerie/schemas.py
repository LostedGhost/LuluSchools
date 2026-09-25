from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.messagerie.models import TypeConversation


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant_id: str


class ConversationOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    type: TypeConversation
    classe_id: str | None
    created_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contenu: str


class MessageOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    conversation_id: str
    auteur_id: str
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
