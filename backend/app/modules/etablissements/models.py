import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TypeEtablissement(str, enum.Enum):
    EP = "EP"
    ES = "ES"
    UP = "UP"


class StatutEtablissement(str, enum.Enum):
    PUBLIC = "public"
    PRIVE = "prive"


class PolitiqueDepassement(str, enum.Enum):
    ORDRE_ARRIVEE = "ordre_arrivee"
    NOTES_CONCOURS = "notes_concours"
    TIRAGE_SORT = "tirage_sort"


class Etablissement(Base):
    __tablename__ = "etablissements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    nom: Mapped[str] = mapped_column(String(200))
    type: Mapped[TypeEtablissement] = mapped_column(Enum(TypeEtablissement))
    statut: Mapped[StatutEtablissement] = mapped_column(Enum(StatutEtablissement))
    code_etablissement: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    classes: Mapped[list["Classe"]] = relationship(back_populates="etablissement")


class AdminEtablissement(Base):
    __tablename__ = "admins_etablissement"

    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), primary_key=True)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)

    etablissement: Mapped[Etablissement] = relationship()


class Classe(Base):
    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    niveau: Mapped[str] = mapped_column(String(100))
    capacite: Mapped[int] = mapped_column(Integer)
    politique_depassement: Mapped[PolitiqueDepassement] = mapped_column(Enum(PolitiqueDepassement))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    etablissement: Mapped[Etablissement] = relationship(back_populates="classes")
