import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TypeVisiteVirtuelle(str, enum.Enum):
    TROIS_D = "3d"
    DRONE = "drone"


class VisiteVirtuelle(Base):
    """UC-19. `attestation_autorisation` : engagement declaratif de l'etablissement
    (autorisation de vol de drone aupres de l'ANAC, droit a l'image des personnes
    filmees - Art. 576) - LuluSchools ne peut pas verifier ces points elle-meme, voir
    docs/cas-utilisation-phase-2-3.md UC-19."""

    __tablename__ = "visites_virtuelles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissements.id"), index=True)
    type: Mapped[TypeVisiteVirtuelle] = mapped_column(Enum(TypeVisiteVirtuelle))
    lien_externe: Mapped[str] = mapped_column(Text)
    attestation_autorisation: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
