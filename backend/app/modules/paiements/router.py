import hmac
import logging

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import api_error
from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.billetterie.models import BilletEvenement, StatutBillet
from app.modules.marketplace.models import StatutTransactionMarketplace, TransactionMarketplace
from app.modules.micro_jobs.models import OffreMicroJob, StatutOffreMicroJob
from app.modules.paiements.schemas import KkiapayWebhookPayload
from app.modules.services_scolaires.models import StatutTicket, TicketCantine, TicketTransport

router = APIRouter(tags=["paiements"])

logger = logging.getLogger(__name__)


def _montant_correspond(prix_attendu: float, montant_recu: float) -> bool:
    """Bug reel corrige (audit securite, 2026-09-26) : le webhook ne verifiait jamais
    que le montant reellement paye chez Kkiapay correspondait au prix de la ressource
    a laquelle le transactionId a ete rattache via `.../paiement/amorcer` - un appelant
    pouvait payer un montant derisoire puis l'associer a une ressource bien plus chere.
    Tolerance de 1 FCFA pour absorber un eventuel arrondi flottant, jamais pour laisser
    passer un ecart reel."""
    return abs(prix_attendu - montant_recu) < 1


def _confirmer_demande_acte(db: Session, transaction_id: str, montant: float) -> bool:
    demande = (
        db.query(DemandeActeAcademique)
        .filter(DemandeActeAcademique.kkiapay_transaction_id == transaction_id)
        .first()
    )
    if demande is None or demande.statut != StatutDemandeActe.SOUMISE:
        return False
    type_acte = db.get(TypeActeAcademique, demande.type_acte_id) if demande.type_acte_id else None
    prix_attendu = type_acte.prix if type_acte is not None else 0.0
    if not _montant_correspond(prix_attendu, montant):
        logger.warning(
            "webhook_kkiapay: montant recu (%s) different du prix attendu (%s) pour la demande d'acte %s "
            "- paiement refuse.",
            montant, prix_attendu, demande.id,
        )
        return False
    demande.paiement_confirme = True
    demande.statut = StatutDemandeActe.EN_TRAITEMENT
    db.commit()
    return True


def _confirmer_ticket_transport(db: Session, transaction_id: str, montant: float) -> bool:
    ticket = (
        db.query(TicketTransport).filter(TicketTransport.kkiapay_transaction_id == transaction_id).first()
    )
    if ticket is None or ticket.statut != StatutTicket.ACHETE or ticket.paiement_confirme:
        return False
    if not _montant_correspond(ticket.prix_paye, montant):
        logger.warning(
            "webhook_kkiapay: montant recu (%s) different du prix attendu (%s) pour le ticket transport %s "
            "- paiement refuse.",
            montant, ticket.prix_paye, ticket.id,
        )
        return False
    ticket.paiement_confirme = True
    db.commit()
    return True


def _confirmer_ticket_cantine(db: Session, transaction_id: str, montant: float) -> bool:
    ticket = db.query(TicketCantine).filter(TicketCantine.kkiapay_transaction_id == transaction_id).first()
    if ticket is None or ticket.statut != StatutTicket.ACHETE or ticket.paiement_confirme:
        return False
    if not _montant_correspond(ticket.prix_paye, montant):
        logger.warning(
            "webhook_kkiapay: montant recu (%s) different du prix attendu (%s) pour le ticket cantine %s "
            "- paiement refuse.",
            montant, ticket.prix_paye, ticket.id,
        )
        return False
    ticket.paiement_confirme = True
    db.commit()
    return True


def _confirmer_billet_evenement(db: Session, transaction_id: str, montant: float) -> bool:
    billet = (
        db.query(BilletEvenement).filter(BilletEvenement.kkiapay_transaction_id == transaction_id).first()
    )
    if billet is None or billet.statut != StatutBillet.ACHETE or billet.paiement_confirme:
        return False
    if not _montant_correspond(billet.prix_paye, montant):
        logger.warning(
            "webhook_kkiapay: montant recu (%s) different du prix attendu (%s) pour le billet %s "
            "- paiement refuse.",
            montant, billet.prix_paye, billet.id,
        )
        return False
    billet.paiement_confirme = True
    db.commit()
    return True


def _confirmer_offre_micro_job(db: Session, transaction_id: str, montant: float) -> bool:
    offre = db.query(OffreMicroJob).filter(OffreMicroJob.kkiapay_transaction_id == transaction_id).first()
    if (
        offre is None
        or offre.statut != StatutOffreMicroJob.EN_ATTENTE_PAIEMENT
        or offre.paiement_confirme
    ):
        return False
    if not _montant_correspond(offre.prix, montant):
        logger.warning(
            "webhook_kkiapay: montant recu (%s) different du prix attendu (%s) pour l'offre micro-job %s "
            "- paiement refuse.",
            montant, offre.prix, offre.id,
        )
        return False
    offre.paiement_confirme = True
    offre.statut = StatutOffreMicroJob.OUVERTE
    db.commit()
    return True


def _confirmer_transaction_marketplace(db: Session, transaction_id: str, montant: float) -> bool:
    transaction = (
        db.query(TransactionMarketplace)
        .filter(TransactionMarketplace.kkiapay_transaction_id == transaction_id)
        .first()
    )
    if (
        transaction is None
        or transaction.statut != StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT
        or transaction.paiement_confirme
    ):
        return False
    if not _montant_correspond(transaction.prix_paye, montant):
        logger.warning(
            "webhook_kkiapay: montant recu (%s) different du prix attendu (%s) pour la transaction "
            "marketplace %s - paiement refuse.",
            montant, transaction.prix_paye, transaction.id,
        )
        return False
    transaction.paiement_confirme = True
    transaction.statut = StatutTransactionMarketplace.PAIEMENT_CONFIRME
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
    offres micro-job) - une seule d'entre elles correspondra."""
    if not x_kkiapay_secret or not hmac.compare_digest(x_kkiapay_secret, settings.kkiapay_secret):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "secret_invalide", "Secret webhook invalide.")

    if payload.event == "transaction.success" and payload.isPaymentSucces:
        (
            _confirmer_demande_acte(db, payload.transactionId, payload.amount)
            or _confirmer_ticket_transport(db, payload.transactionId, payload.amount)
            or _confirmer_ticket_cantine(db, payload.transactionId, payload.amount)
            or _confirmer_billet_evenement(db, payload.transactionId, payload.amount)
            or _confirmer_offre_micro_job(db, payload.transactionId, payload.amount)
            or _confirmer_transaction_marketplace(db, payload.transactionId, payload.amount)
        )

    return {"ok": True}
