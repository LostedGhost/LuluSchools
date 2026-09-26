import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CategorieAnnonce(str, enum.Enum):
    FOURNITURES_SCOLAIRES = "fournitures_scolaires"
    MANUELS_LIVRES = "manuels_livres"
    VETEMENTS_UNIFORMES = "vetements_uniformes"
    ELECTRONIQUE = "electronique"
    AUTRE = "autre"


class EtatArticle(str, enum.Enum):
    NEUF = "neuf"
    TRES_BON_ETAT = "tres_bon_etat"
    BON_ETAT = "bon_etat"
    USE = "use"


class StatutAnnonce(str, enum.Enum):
    DISPONIBLE = "disponible"
    RESERVEE = "reservee"
    VENDUE = "vendue"
    RETIREE = "retiree"


class StatutTransactionMarketplace(str, enum.Enum):
    EN_ATTENTE_PAIEMENT = "en_attente_paiement"
    PAIEMENT_CONFIRME = "paiement_confirme"
    REMISE_DECLAREE = "remise_declaree"
    CONFIRMEE = "confirmee"
    CONTESTEE = "contestee"
    FINALISEE = "finalisee"
    REMBOURSEE = "remboursee"
    ANNULEE = "annulee"


class StatutContestationMarketplace(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    ACCEPTEE = "acceptee"
    REJETEE = "rejetee"


class AnnonceMarketplace(Base):
    """UC-20. Reservee aux eleves >=16 ans (AGE_MAJORITE_NUMERIQUE, meme seuil que
    l'auto-validation d'inscription, Art. 446 - voir app/modules/inscriptions/router.py).
    `etablissement_id` est denormalise, fixe une fois pour toutes a la publication
    (etablissement du vendeur a ce moment-la), pas recalcule dynamiquement ensuite -
    coherent avec LigneTransport/Evenement (Phase 2/3), pas avec le calcul dynamique de
    la messagerie (qui doit lui rester a jour en continu pour un groupe de classe)."""

    __tablename__ = "annonces_marketplace"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    vendeur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    titre: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    categorie: Mapped[CategorieAnnonce] = mapped_column(Enum(CategorieAnnonce))
    etat: Mapped[EtatArticle] = mapped_column(Enum(EtatArticle))
    prix: Mapped[float] = mapped_column(Float)
    statut: Mapped[StatutAnnonce] = mapped_column(Enum(StatutAnnonce), default=StatutAnnonce.DISPONIBLE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PhotoAnnonceMarketplace(Base):
    """Au moins une photo obligatoire a la creation (UC-20, verifie cote router, pas ici :
    pas de contrainte "au moins 1" exprimable simplement au niveau table)."""

    __tablename__ = "photos_annonce_marketplace"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    annonce_id: Mapped[str] = mapped_column(ForeignKey("annonces_marketplace.id"), index=True)
    lulufiles_file_id: Mapped[str] = mapped_column(String(100))
    ordre: Mapped[int] = mapped_column(Integer, default=0)


class SignalementAnnonceMarketplace(Base):
    __tablename__ = "signalements_annonce_marketplace"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    annonce_id: Mapped[str] = mapped_column(ForeignKey("annonces_marketplace.id"), index=True)
    signale_par_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"))
    traite: Mapped[bool] = mapped_column(Boolean, default=False)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    traite_par_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TransactionMarketplace(Base):
    """Sequestre "Option A", meme modele qu'UC-18 (ADR-008) : le paiement de l'acheteur
    est encaisse sur le compte Kkiapay unique de LuluSchools, le sequestre n'est qu'un
    statut suivi ici. `annonce_id` n'est PAS unique : une premiere transaction annulee/
    remboursee ne doit jamais bloquer une reservation ulterieure de la meme annonce -
    seule une transaction dans un statut non terminal empeche une nouvelle reservation
    (verifie via le statut de l'Annonce elle-meme, pas une contrainte d'unicite ici)."""

    __tablename__ = "transactions_marketplace"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    annonce_id: Mapped[str] = mapped_column(ForeignKey("annonces_marketplace.id"), index=True)
    acheteur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    statut: Mapped[StatutTransactionMarketplace] = mapped_column(
        Enum(StatutTransactionMarketplace), default=StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT
    )
    prix_paye: Mapped[float] = mapped_column(Float)
    paiement_confirme: Mapped[bool] = mapped_column(Boolean, default=False)
    kkiapay_transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    date_remise_declaree: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_limite_confirmation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_paiement_vendeur: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ContestationMarketplace(Base):
    __tablename__ = "contestations_marketplace"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions_marketplace.id"), unique=True, index=True)
    motif: Mapped[str] = mapped_column(Text)
    statut: Mapped[StatutContestationMarketplace] = mapped_column(
        Enum(StatutContestationMarketplace), default=StatutContestationMarketplace.EN_ATTENTE
    )
    decision_motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_par_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
