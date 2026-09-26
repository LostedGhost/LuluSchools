import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatutSessionLive(str, enum.Enum):
    PLANIFIEE = "planifiee"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"


class SessionLive(Base):
    __tablename__ = "sessions_live"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignants.utilisateur_id"), index=True)
    date_heure: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    statut: Mapped[StatutSessionLive] = mapped_column(Enum(StatutSessionLive), default=StatutSessionLive.PLANIFIEE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ConsentementCameraLive(Base):
    """UC-16 : consentement explicite et horodate du tuteur, distinct du consentement
    d'inscription (extension d'Art. 446) - un seul par eleve, valable pour toutes les
    sessions live futures une fois donne."""

    __tablename__ = "consentements_camera_live"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), unique=True, index=True)
    tuteur_id: Mapped[str] = mapped_column(ForeignKey("tuteurs.utilisateur_id"))
    date_consentement: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ParticipationLive(Base):
    __tablename__ = "participations_live"
    __table_args__ = (UniqueConstraint("session_id", "eleve_utilisateur_id", name="uq_participation_live"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_live.id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    camera_autorisee: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# --- UC-25 : tableau de classe collaboratif ("craie/chiffon") ---


class PanneauTableau(Base):
    """Un tableau se compose de plusieurs panneaux qu'on 'fait glisser' (comme les
    volets d'un vrai tableau noir physique) plutot qu'un unique canvas infini - voir
    cahier des charges §3.1. Le panneau 0 est cree paresseusement au premier acces."""

    __tablename__ = "panneaux_tableau"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_live.id"), index=True)
    ordre: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TypeTraitTableau(str, enum.Enum):
    TRAIT_LIBRE = "trait_libre"  # a main levee (doigt/stylet) - "craie"
    TEXTE = "texte"  # bloc tapable au clavier, positionnable
    EFFACEMENT = "effacement"  # "coup de chiffon" - efface tout le panneau a cet instant


class TraitTableau(Base):
    """Historique append-only des traces du tableau - jamais mutees ni supprimees, ce qui
    permet a la fois le rejeu 'time-lapse' (rejouer les traits dans l'ordre) et une
    convergence naturelle entre plusieurs redacteurs simultanement autorises (chaque
    trait est un objet independant, aucun n'ecrase celui d'un autre - voir cahier des
    charges §3.1, 'edition concurrente sans collision'). `donnees` porte les points
    normalises (0..1) d'un trait libre, ou la position/texte d'un bloc texte ; vide pour
    un effacement."""

    __tablename__ = "traits_tableau"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    panneau_id: Mapped[str] = mapped_column(ForeignKey("panneaux_tableau.id"), index=True)
    auteur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    type: Mapped[TypeTraitTableau] = mapped_column(Enum(TypeTraitTableau))
    donnees: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ModePermissionEcriture(str, enum.Enum):
    PRETEE = "pretee"  # accordee directement par le professeur, persistante
    ACCORDEE = "accordee"  # accordee suite a une DemandeCraie


class PermissionEcritureTableau(Base):
    """Tant qu'aucune ligne n'existe pour (session, eleve), l'eleve ne peut que LIRE le
    tableau. Le professeur peut revoquer a tout instant (supprime la ligne), y compris en
    plein trait - le prochain envoi de l'eleve sera simplement refuse."""

    __tablename__ = "permissions_ecriture_tableau"
    __table_args__ = (UniqueConstraint("session_id", "eleve_utilisateur_id", name="uq_permission_ecriture_tableau"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_live.id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    mode: Mapped[ModePermissionEcriture] = mapped_column(Enum(ModePermissionEcriture))
    accordee_par_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class StatutDemandeCraie(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    ACCORDEE = "accordee"
    REFUSEE = "refusee"


class DemandeCraie(Base):
    """'Lever la main pour demander la craie' - file d'attente cote professeur (voir
    cahier des charges §3.1)."""

    __tablename__ = "demandes_craie"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_live.id"), index=True)
    eleve_utilisateur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    statut: Mapped[StatutDemandeCraie] = mapped_column(Enum(StatutDemandeCraie), default=StatutDemandeCraie.EN_ATTENTE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CaptureTableauSession(Base):
    """UC-25.6 : capture automatique d'un panneau a la cloture de la session (rendu PNG
    via PyMuPDF a partir des traits, voir rendu_tableau.py) - consultable independamment
    d'un cours (integration au cahier de textes en 'Mes cours' laissee en P2, voir
    cahier des charges)."""

    __tablename__ = "captures_tableau_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_live.id"), index=True)
    panneau_id: Mapped[str] = mapped_column(ForeignKey("panneaux_tableau.id"), index=True)
    lulufiles_file_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ResumeSessionLive(Base):
    """UC-33.1 : observation asynchrone du tuteur - resume texte genere par FreeLLM a la
    cloture de la session, a partir du chat + du contenu textuel du tableau. Un seul
    resume par session (partage entre tous les tuteurs des eleves ayant participe -
    voir router.py::obtenir_resume_session_live_pour_tuteur), jamais un flux video/audio
    enregistre (UC-33.2 : le tuteur ne rejoint jamais la session en direct)."""

    __tablename__ = "resumes_session_live"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_live.id"), unique=True, index=True)
    contenu: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MessageSessionLive(Base):
    """Discussion textuelle de la session (salle sociale avant l'heure incluse, voir
    cahier des charges §3.2) - immuable, comme la messagerie generale (jamais de
    suppression reelle), mais volontairement un circuit dedie et plus simple (pas de
    signalement/masquage individuel dans cette premiere version - voir limites connues)."""

    __tablename__ = "messages_session_live"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions_live.id"), index=True)
    auteur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    contenu: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
