import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatutTicket(str, enum.Enum):
    ACHETE = "achete"
    VALIDE = "valide"
    EXPIRE = "expire"
    REMBOURSE = "rembourse"


class LigneTransport(Base):
    """UC-11 : catalogue defini par etablissement (A+) - prix, capacite par trajet."""

    __tablename__ = "lignes_transport"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    nom: Mapped[str] = mapped_column(String(200))
    prix: Mapped[float] = mapped_column(Float)
    capacite_par_trajet: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TicketTransport(Base):
    __tablename__ = "tickets_transport"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    ligne_id: Mapped[str] = mapped_column(ForeignKey("lignes_transport.id"), index=True)
    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    date_trajet: Mapped[date] = mapped_column(Date)
    statut: Mapped[StatutTicket] = mapped_column(Enum(StatutTicket, name="statutticket"), default=StatutTicket.ACHETE)
    prix_paye: Mapped[float] = mapped_column(Float)
    paiement_confirme: Mapped[bool] = mapped_column(Boolean, default=False)
    kkiapay_transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TypeRepasCantine(Base):
    """UC-12 : catalogue defini par etablissement (A+) - prix, capacite de service par jour."""

    __tablename__ = "types_repas_cantine"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    nom: Mapped[str] = mapped_column(String(200))
    prix: Mapped[float] = mapped_column(Float)
    capacite_par_jour: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TicketCantine(Base):
    __tablename__ = "tickets_cantine"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    type_repas_id: Mapped[str] = mapped_column(ForeignKey("types_repas_cantine.id"), index=True)
    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    date_service: Mapped[date] = mapped_column(Date)
    statut: Mapped[StatutTicket] = mapped_column(Enum(StatutTicket, name="statutticket"), default=StatutTicket.ACHETE)
    prix_paye: Mapped[float] = mapped_column(Float)
    paiement_confirme: Mapped[bool] = mapped_column(Boolean, default=False)
    kkiapay_transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
