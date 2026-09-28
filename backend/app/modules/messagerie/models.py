import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TypeConversation(str, enum.Enum):
    DM = "dm"
    GROUPE_CLASSE = "groupe_classe"


class Conversation(Base):
    """UC-13. Un groupe_classe est cree automatiquement a la creation de la Classe
    (voir app/modules/etablissements/router.py) - une seule par classe (`classe_id`
    unique). Son appartenance n'est PAS stockee dans ParticipantConversation : elle est
    calculee dynamiquement (eleves inscrits VALIDEE + leurs tuteurs + enseignants sous
    contrat SIGNE avec l'etablissement de la classe), pour rester automatiquement a jour
    sans hook a maintenir dans les modules inscriptions/recrutement. ParticipantConversation
    ne sert donc qu'aux conversations de type DM."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    type: Mapped[TypeConversation] = mapped_column(Enum(TypeConversation))
    classe_id: Mapped[str | None] = mapped_column(ForeignKey("classes.id"), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ParticipantConversation(Base):
    __tablename__ = "participants_conversation"

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), primary_key=True)
    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), primary_key=True)


class Message(Base):
    """`masque_par` : liste des identifiants d'utilisateurs ayant masque le message de
    leur cote (UC-13, delegue) - jamais une suppression reelle de la ligne : toute
    conversation impliquant un eleve doit rester journalisee de facon inalterable
    (Art. 519/521/550)."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    auteur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    contenu: Mapped[str] = mapped_column(Text)
    masque_par: Mapped[list] = mapped_column(JSON, default=list)
    # Lot 7.4 : message vocal (LuluFiles) pour qui ne sait pas ou peu ecrire ; `contenu`
    # garde une trace lisible (« Message vocal (0:12) ») pour la moderation et les listes.
    audio_lulufiles_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    duree_audio_s: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def est_vocal(self) -> bool:
        return self.audio_lulufiles_id is not None
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SignalementMessage(Base):
    __tablename__ = "signalements_message"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    signale_par_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"))
    traite: Mapped[bool] = mapped_column(Boolean, default=False)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    traite_par_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True)
    # Triage IA (core/moderation.py) : aide a la decision, jamais la decision.
    ia_gravite: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ia_resume: Mapped[str | None] = mapped_column(Text, nullable=True)
    ia_decision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
