import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RoleUtilisateur(str, enum.Enum):
    TUTEUR = "tuteur"
    ELEVE = "eleve"
    ENSEIGNANT = "enseignant"
    ADMIN_ETABLISSEMENT = "admin_etablissement"
    ADMIN_MINISTERIEL = "admin_ministeriel"


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    # Identifiant de connexion : l'e-mail pour tuteur/enseignant/admin, le matricule pour un eleve
    # (compte auto-cree sans e-mail propre a l'inscription, voir UC-02/UC-03).
    login_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    mot_de_passe_temporaire: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[RoleUtilisateur] = mapped_column(Enum(RoleUtilisateur))
    email_verifie: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tuteur: Mapped["Tuteur | None"] = relationship(back_populates="utilisateur", uselist=False)
    otp_verifications: Mapped[list["OtpVerification"]] = relationship(back_populates="utilisateur")


class Tuteur(Base):
    __tablename__ = "tuteurs"

    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), primary_key=True)
    piece_identite_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    piece_identite_numero: Mapped[str | None] = mapped_column(String(100), nullable=True)

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="tuteur")


class OtpVerification(Base):
    __tablename__ = "otp_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    salt: Mapped[str] = mapped_column(String(32))
    tentatives: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    utilisee: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    utilisateur: Mapped[Utilisateur] = relationship(back_populates="otp_verifications")
