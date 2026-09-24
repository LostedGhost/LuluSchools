import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatutPoste(str, enum.Enum):
    OUVERT = "ouvert"
    POURVU = "pourvu"
    NON_POURVU = "non_pourvu"


class StatutCandidature(str, enum.Enum):
    EN_EVALUATION = "en_evaluation"
    RETENUE = "retenue"
    REJETEE = "rejetee"


class StatutDocument(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    NOTE = "note"
    ECHEC_NOTATION = "echec_notation"


class StatutVerificationCasier(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    CONFORME = "conforme"
    NON_CONFORME = "non_conforme"


class StatutContestation(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    ACCEPTEE = "acceptee"
    REJETEE = "rejetee"


class StatutContrat(str, enum.Enum):
    EN_ATTENTE_SIGNATURE = "en_attente_signature"
    SIGNE = "signe"


class StatutProposition(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    ACCEPTEE = "acceptee"
    REFUSEE = "refusee"


class Poste(Base):
    __tablename__ = "postes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    titre: Mapped[str] = mapped_column(String(200))
    statut: Mapped[StatutPoste] = mapped_column(Enum(StatutPoste), default=StatutPoste.OUVERT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    criteres: Mapped[list["CritereDocumentPoste"]] = relationship(back_populates="poste")


class CritereDocumentPoste(Base):
    __tablename__ = "criteres_document_poste"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    poste_id: Mapped[str] = mapped_column(ForeignKey("postes.id"), index=True)
    type_document: Mapped[str] = mapped_column(String(100))
    coefficient: Mapped[float] = mapped_column(Float)
    seuil_minimal: Mapped[float] = mapped_column(Float)

    poste: Mapped[Poste] = relationship(back_populates="criteres")


class Candidature(Base):
    __tablename__ = "candidatures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    poste_id: Mapped[str] = mapped_column(ForeignKey("postes.id"), index=True)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignants.utilisateur_id"), index=True)
    statut: Mapped[StatutCandidature] = mapped_column(Enum(StatutCandidature))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    documents: Mapped[list["DocumentCandidature"]] = relationship(back_populates="candidature")
    verification_casier: Mapped["VerificationCasierJudiciaire | None"] = relationship(
        back_populates="candidature", uselist=False
    )


class DocumentCandidature(Base):
    __tablename__ = "documents_candidature"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    candidature_id: Mapped[str] = mapped_column(ForeignKey("candidatures.id"), index=True)
    type_document: Mapped[str] = mapped_column(String(100))
    lulufiles_file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note_ia: Mapped[float | None] = mapped_column(Float, nullable=True)
    statut: Mapped[StatutDocument] = mapped_column(Enum(StatutDocument), default=StatutDocument.EN_ATTENTE)

    candidature: Mapped[Candidature] = relationship(back_populates="documents")


class VerificationCasierJudiciaire(Base):
    """Ecarte du pipeline de notation IA generique (Art. 395 - regime restreint des
    donnees penales) : fichier garde localement, jamais sur LuluFiles/Telegram, acces
    reserve aux personnes designees par l'A+ (a appliquer au niveau de l'endpoint de
    lecture, pas encore construit - voir rapport final)."""

    __tablename__ = "verifications_casier_judiciaire"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    candidature_id: Mapped[str] = mapped_column(ForeignKey("candidatures.id"), unique=True)
    chemin_fichier_local: Mapped[str] = mapped_column(String(500))
    statut: Mapped[StatutVerificationCasier] = mapped_column(
        Enum(StatutVerificationCasier), default=StatutVerificationCasier.EN_ATTENTE
    )
    verifie_par_utilisateur_id: Mapped[str | None] = mapped_column(
        ForeignKey("utilisateurs.id"), nullable=True
    )
    date_verification: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_suppression_prevue: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    candidature: Mapped[Candidature] = relationship(back_populates="verification_casier")


class Contestation(Base):
    __tablename__ = "contestations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    candidature_id: Mapped[str] = mapped_column(ForeignKey("candidatures.id"), index=True)
    motif: Mapped[str] = mapped_column(Text)
    statut: Mapped[StatutContestation] = mapped_column(
        Enum(StatutContestation), default=StatutContestation.EN_ATTENTE
    )
    motif_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Contrat(Base):
    __tablename__ = "contrats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    candidature_id: Mapped[str] = mapped_column(ForeignKey("candidatures.id"), index=True)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignants.utilisateur_id"), index=True)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    syllabus: Mapped[str] = mapped_column(Text)
    date_fin: Mapped[date] = mapped_column(Date)
    statut: Mapped[StatutContrat] = mapped_column(
        Enum(StatutContrat), default=StatutContrat.EN_ATTENTE_SIGNATURE
    )
    signature_horodatage: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signature_hash_document: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PropositionReconduction(Base):
    __tablename__ = "propositions_reconduction"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    contrat_precedent_id: Mapped[str] = mapped_column(ForeignKey("contrats.id"), index=True)
    nouveau_contrat_id: Mapped[str | None] = mapped_column(ForeignKey("contrats.id"), nullable=True)
    statut: Mapped[StatutProposition] = mapped_column(
        Enum(StatutProposition), default=StatutProposition.EN_ATTENTE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
