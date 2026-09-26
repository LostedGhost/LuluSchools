import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def annee_academique_courante() -> str:
    """UC-43/58 : format "AAAA-AAAA+1" - la rentree beninoise demarre en septembre, donc
    tout mois >= septembre appartient a l'annee academique qui commence cette annee civile,
    les autres mois (janvier-aout) appartiennent a l'annee academique commencee l'annee
    civile precedente. Utilise comme valeur par defaut quand aucune annee n'est precisee
    explicitement (creation de classe, calcul de portee) - jamais pour trancher une regle
    metier, juste un repli raisonnable."""
    aujourd_hui = _utcnow()
    premiere_annee = aujourd_hui.year if aujourd_hui.month >= 9 else aujourd_hui.year - 1
    return f"{premiere_annee}-{premiere_annee + 1}"


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
    # Texte libre affiche sur la fiche etablissement (UC-23, lot admin ministeriel) - meme
    # esprit que EtablissementPhoto, jamais obligatoire (aucun etablissement existant n'en a).
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Homologation active/suspendue (UC-26/UC-42) - distinct de `statut` (public/prive, une
    # caracteristique administrative, pas un etat du cycle de vie). Defaut true : aucun
    # etablissement existant n'est suspendu par cette migration.
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
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
    # UC-43/58 (lot admin etablissement) : texte libre, jamais une enumeration globale -
    # les filieres universitaires sont propres a chaque etablissement (pool different par
    # etablissement, voir scripts/seed_mega.py) et les sections EP/ES (A/B/C) sont
    # arbitraires par etablissement. Le frontend propose un <select> ferme pour `niveau`
    # (taxonomie nationale reprise de seed_mega.py) mais jamais pour `filiere`.
    filiere: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # UC-43/44/58 : dimension manquante jusqu'ici - une classe existait perpetuellement,
    # sans notion de rentree. Format "AAAA-AAAA+1" (annee_academique_courante()).
    annee_academique: Mapped[str] = mapped_column(String(20))
    # UC-44/59 : trace la reconduction d'une annee sur l'autre (pas une contrainte forte -
    # une classe reconduite peut ensuite etre modifiee librement, la tracabilite reste
    # informative, pas structurante).
    reconduite_depuis_id: Mapped[str | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    capacite: Mapped[int] = mapped_column(Integer)
    politique_depassement: Mapped[PolitiqueDepassement] = mapped_column(Enum(PolitiqueDepassement))
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    classe: Mapped["Classe"] = relationship()


class StatutRentree(str, enum.Enum):
    OUVERTE = "ouverte"
    FERMEE = "fermee"


class RentreeScolaire(Base):
    """UC-39/55 (lot admin etablissement) : declare l'ouverture d'une annee academique a
    l'inscription pour un etablissement. Une seule rentree OUVERTE par etablissement a la
    fois (verifie en applicatif, pas une contrainte SQL - meme convention que le reste du
    projet, cf. RentreeScolaire.statut dans le routeur)."""

    __tablename__ = "rentrees_scolaires"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    annee_academique: Mapped[str] = mapped_column(String(20))
    statut: Mapped[StatutRentree] = mapped_column(Enum(StatutRentree), default=StatutRentree.OUVERTE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


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
