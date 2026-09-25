import hmac

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import api_error
from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe
from app.modules.paiements.schemas import KkiapayWebhookPayload

router = APIRouter(tags=["paiements"])


def _confirmer_demande_acte(db: Session, transaction_id: str) -> bool:
    demande = (
        db.query(DemandeActeAcademique)
        .filter(DemandeActeAcademique.kkiapay_transaction_id == transaction_id)
        .first()
    )
    if demande is None or demande.statut != StatutDemandeActe.SOUMISE:
        return False
    demande.paiement_confirme = True
    demande.statut = StatutDemandeActe.EN_TRAITEMENT
    db.commit()
    return True


@router.post("/paiements/webhook/kkiapay", include_in_schema=False)
def webhook_kkiapay(
    payload: KkiapayWebhookPayload,
    db: Session = Depends(get_db),
    x_kkiapay_secret: str | None = Header(default=None),
) -> dict:
    """URL UNIQUE et fixe pour TOUT le compte Kkiapay de LuluSchools (a renseigner une
    fois dans leur tableau de bord), jamais une par ressource - voir
    docs/contrat-api-phase1.md et docs/contrat-api-phase2-3.md. Verifie le secret
    partage (KKIAPAY_SECRET) renvoye tel quel dans l'en-tete x-kkiapay-secret, puis
    essaie de rattacher la transaction a chacun des types de ressources payantes de la
    plateforme (actes academiques, tickets transport/cantine, billets d'evenement,
    missions micro-job) - une seule d'entre elles correspondra."""
    if not x_kkiapay_secret or not hmac.compare_digest(x_kkiapay_secret, settings.kkiapay_secret):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "secret_invalide", "Secret webhook invalide.")

    if payload.event == "transaction.success" and payload.isPaymentSucces:
        _confirmer_demande_acte(db, payload.transactionId)

    return {"ok": True}
