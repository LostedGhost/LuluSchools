import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def annee_academique_courante(reference: date | None = None) -> str:
    """Annee scolaire au format 'YYYY-YYYY' - rentree fixee au 1er septembre (convention
    Afrique de l'Ouest francophone). UC-24 : une Classe est une instance annuelle precise
    (une '6eme A' en 2025-2026 n'est pas la meme instance qu'en 2026-2027), ce qui suffit a
    scoper aussi les affectations enseignant et les inscriptions eleve sans toucher a leur
    schema - elles pointent deja vers une Classe, donc vers une annee, via classe_id."""
    aujourdhui = reference or datetime.now(timezone.utc).date()
    if aujourdhui.month >= 9:
        return f"{aujourdhui.year}-{aujourdhui.year + 1}"
    return f"{aujourdhui.year - 1}-{aujourdhui.year}"


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
    # Nullable en base pour ne jamais casser une ligne pre-existante a la migration,
    # mais exigees par EtablissementCreate (obligatoires pour toute nouvelle creation) -
    # objectif produit : une geolocalisation pour TOUS les etablissements, a terme.
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    annee_academique: Mapped[str] = mapped_column(String(9), default=annee_academique_courante, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    etablissement: Mapped[Etablissement] = relationship(back_populates="classes")


class AffectationEnseignant(Base):
    """Lie un enseignant a une classe PRECISE dont il a la charge (constat d'audit RBAC :
    auparavant, le seul lien disponible etait Contrat.enseignant_id, a l'echelle de
    l'etablissement entier - n'importe quel enseignant sous contrat signe pouvait donc
    gerer les cours/devoirs de N'IMPORTE QUELLE classe de son etablissement, pas
    seulement les siennes). Geree par un A+/A++ (voir POST /classes/{classe_id}/affectations),
    et devenue le vrai filtre pour create/gerer cours, quiz, devoirs, sessions live."""

    __tablename__ = "affectations_enseignant"
    __table_args__ = (UniqueConstraint("enseignant_id", "classe_id", name="uq_affectation_enseignant_classe"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    # UC-23 : au plus un professeur principal par classe (voir vie_scolaire) - il voit la
    # vie scolaire complete de la classe, un enseignant de matiere ne voit que ses propres
    # entrees. Invariant applique cote applicatif (POST .../professeur-principal), pas par
    # une contrainte SQL - coherent avec le reste du module (ex. capacite de la classe).
    est_professeur_principal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    classe: Mapped["Classe"] = relationship()


class EtablissementPhoto(Base):
    """Photo d'un etablissement pour l'annuaire public (vitrine/marketplace). Le fichier
    reel est stocke sur LuluFiles (ADR-003) : seul l'id du fichier est conserve ici, un
    lien signe est genere a la demande (voir GET /etablissements/{id}/photos-publiques)."""

    __tablename__ = "etablissement_photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    lulufiles_file_id: Mapped[str] = mapped_column(String(100))
    ordre: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    etablissement: Mapped[Etablissement] = relationship()
