import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.inscriptions.models import Eleve


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatutDemandeActe(str, enum.Enum):
    SOUMISE = "soumise"
    EN_TRAITEMENT = "en_traitement"
    ACCEPTEE = "acceptee"
    REJETEE = "rejetee"


class TypeActeAcademique(Base):
    """UC-10 : catalogue configurable par etablissement (revise a partir d'un exemple
    reel de bareme universitaire - IFRI, voir cas-utilisation-phase-1.md). Chaque
    etablissement definit ses propres types (nom, prix, pieces requises en texte libre,
    condition d'eligibilite optionnelle)."""

    __tablename__ = "types_acte_academique"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    nom: Mapped[str] = mapped_column(String(200))
    prix: Mapped[float] = mapped_column(Float, default=0)
    pieces_requises: Mapped[str] = mapped_column(Text)
    condition_eligibilite: Mapped[str | None] = mapped_column(Text, nullable=True)
    # UC-50/64 (lot admin etablissement) : meme moteur que Poste.schema_formulaire
    # (recrutement/models.py) - un seul JSON schema pour les deux usages. `pieces_requises`
    # (texte libre existant) reste pour compatibilite descriptive, mais n'est plus le
    # mecanisme de collecte pour une nouvelle demande des que ce champ est renseigne.
    schema_formulaire: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Acte standard genere et livre automatiquement des le paiement (actes/generation.py) :
    # "attestation_scolarite" ou "releve_notes" ; None = traitement manuel par l'A+.
    modele_document: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DemandeActeAcademique(Base):
    __tablename__ = "demandes_acte_academique"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleves.id"), index=True)
    type_acte_id: Mapped[str | None] = mapped_column(ForeignKey("types_acte_academique.id"), nullable=True)
    est_reclamation: Mapped[bool] = mapped_column(Boolean, default=False)
    reference_evaluation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    # UC-51/65 : reponses au schema_formulaire du type d'acte - meme forme que
    # Candidature.reponses_formulaire (recrutement/models.py).
    reponses_formulaire: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # UC-52/66 : resout l'ecart deja documente (aucune livraison de document) - renseigne
    # par l'A+ au traitement, condition de telechargement (UC-53/67).
    document_final_lulufiles_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    statut: Mapped[StatutDemandeActe] = mapped_column(Enum(StatutDemandeActe), default=StatutDemandeActe.SOUMISE)
    paiement_confirme: Mapped[bool] = mapped_column(Boolean, default=False)
    kkiapay_transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    motif_rejet: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Reclamation : avis prepare par l'IA pour l'A+ (copie, bareme, motif de l'eleve) - une
    # aide a la decision, jamais la decision elle-meme (Art. 401).
    analyse_ia: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    eleve: Mapped[Eleve] = relationship()

    @property
    def eleve_nom(self) -> str:
        """Bug reel corrige (audit frontend, 2026-09-25) : DemandeActeOut ne renvoyait
        que eleve_id, l'A+ ne pouvait pas identifier qui avait soumis une demande sans
        aller la chercher ailleurs (meme constat que sur CandidatureOut)."""
        return self.eleve.nom

    @property
    def eleve_prenom(self) -> str:
        return self.eleve.prenom

    @property
    def eleve_matricule(self) -> str | None:
        return self.eleve.matricule
