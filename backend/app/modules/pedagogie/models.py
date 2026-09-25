import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FormatCours(str, enum.Enum):
    TEXTE = "texte"
    PDF = "pdf"
    AUDIO = "audio"


class Cours(Base):
    __tablename__ = "cours"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignants.utilisateur_id"), index=True)
    titre: Mapped[str] = mapped_column(String(200))
    chapitre: Mapped[str] = mapped_column(String(200))
    format: Mapped[FormatCours] = mapped_column(Enum(FormatCours))
    contenu_texte: Mapped[str | None] = mapped_column(Text, nullable=True)
    lulufiles_file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Quiz(Base):
    """UC-07 : seuil de reussite configurable (defaut 80%), tentatives illimitees. Les
    questions sont generees par le LLM (FreeLLM) a partir du contenu texte du cours,
    format QCM impose (voir app.core.llm.FreeLLMClient.generer_quiz)."""

    __tablename__ = "quiz"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    cours_id: Mapped[str] = mapped_column(ForeignKey("cours.id"), index=True)
    seuil_reussite: Mapped[float] = mapped_column(Float, default=80.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    questions: Mapped[list["QuestionQuiz"]] = relationship(back_populates="quiz")


class QuestionQuiz(Base):
    __tablename__ = "questions_quiz"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quiz.id"), index=True)
    ordre: Mapped[int] = mapped_column(Integer)
    enonce: Mapped[str] = mapped_column(Text)
    choix: Mapped[list] = mapped_column(JSON)
    reponse_correcte_index: Mapped[int] = mapped_column(Integer)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")


class TentativeQuiz(Base):
    __tablename__ = "tentatives_quiz"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quiz.id"), index=True)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    reponses: Mapped[list] = mapped_column(JSON)
    score: Mapped[float] = mapped_column(Float)
    reussie: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
