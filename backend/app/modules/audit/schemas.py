from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JournalAuditOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    acteur_id: str
    action: str
    cible_type: str
    cible_id: str
    motif: str | None
    created_at: datetime


class JournalAuditPageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[JournalAuditOut]
    total: int
    limit: int
    offset: int
