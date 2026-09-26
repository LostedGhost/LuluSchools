import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JournalAuditMinisteriel(Base):
    """UC-36/51/52 (lot admin ministeriel) : trace toute action sensible declenchee par
    l'A++ (suspension de compte, edition/validation de referentiel, arbitrage micro-job,
    masquage de contenu, annulation d'evenement...). Cible polymorphe (`cible_type` +
    `cible_id` brut, pas une FK stricte par type) - meme raisonnement que
    DesignationControleur.evenement_id en Phase 2/3, une table de cibles heterogenes ne
    justifie pas une FK par type cible. Ecrit exclusivement via
    app.core.audit.journaliser_action_ministerielle, jamais construit a la main dans un
    router pour garder un seul point d'entree."""

    __tablename__ = "journal_audit_ministeriel"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    acteur_id: Mapped[str] = mapped_column(ForeignKey("utilisateurs.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    cible_type: Mapped[str] = mapped_column(String(50), index=True)
    cible_id: Mapped[str] = mapped_column(String(36), index=True)
    motif: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
