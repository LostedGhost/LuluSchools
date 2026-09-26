from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.modules.audit.models import JournalAuditMinisteriel
from app.modules.audit.schemas import JournalAuditPageOut
from app.modules.identite.models import RoleUtilisateur, Utilisateur

router = APIRouter(prefix="/admin", tags=["audit"])


@router.get("/journal-audit", response_model=JournalAuditPageOut)
def lister_journal_audit(
    cible_type: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> JournalAuditPageOut:
    """UC-52 : lecture seule, aucune action n'est possible depuis cet ecran - il ne fait
    que rendre visibles les ecritures faites par app.core.audit.journaliser_action_ministerielle
    depuis les autres modules (etablissements, referentiels, micro-jobs, utilisateurs,
    contenus, evenements)."""
    limit = max(1, min(limit, 60))
    offset = max(0, offset)

    requete = db.query(JournalAuditMinisteriel)
    if cible_type:
        requete = requete.filter(JournalAuditMinisteriel.cible_type == cible_type)

    total = requete.with_entities(func.count(JournalAuditMinisteriel.id)).scalar() or 0
    items = requete.order_by(JournalAuditMinisteriel.created_at.desc()).offset(offset).limit(limit).all()
    return JournalAuditPageOut(items=items, total=total, limit=limit, offset=offset)
