import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/health")
def health(response: Response, db: Session = Depends(get_db)) -> dict:
    """Endpoint public assume (aucune authentification) : sonde de disponibilite pour supervision/load balancer."""
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        logger.exception("Health check: base de donnees injoignable")
        database_ok = False

    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "checks": {"database": False}}

    return {"status": "ok", "checks": {"database": True}}
