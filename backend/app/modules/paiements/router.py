import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import get_db, get_session_factory
from app.core.files import LuluFilesClient, get_files_client
from app.modules.actes.generation import livrer_en_arriere_plan
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
    """Tolerance de 1 FCFA pour absorber un arrondi flottant, jamais un ecart reel : un
    appelant ne doit pas pouvoir payer un montant derisoire pour une ressource chere."""
    return abs(prix_attendu - montant_recu) < 1


def _prix_acte(db: Session, demande: DemandeActeAcademique) -> float:
    type_acte = db.get(TypeActeAcademique, demande.type_acte_id) if demande.type_acte_id else None
    return type_acte.prix if type_acte is not None else 0.0


def _en_attente(ressource) -> bool:
    if isinstance(ressource, DemandeActeAcademique):
        return ressource.statut == StatutDemandeActe.SOUMISE
    if isinstance(ressource, (TicketTransport, TicketCantine)):
        return ressource.statut == StatutTicket.ACHETE and not ressource.paiement_confirme
    if isinstance(ressource, BilletEvenement):
        return ressource.statut == StatutBillet.ACHETE and not ressource.paiement_confirme
    if isinstance(ressource, OffreMicroJob):
        return ressource.statut == StatutOffreMicroJob.EN_ATTENTE_PAIEMENT and not ressource.paiement_confirme
    if isinstance(ressource, TransactionMarketplace):
        return ressource.statut == StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT and not ressource.paiement_confirme
    return False


def _prix_attendu(db: Session, ressource) -> float:
    if isinstance(ressource, DemandeActeAcademique):
        return _prix_acte(db, ressource)
    if isinstance(ressource, OffreMicroJob):
        return ressource.prix
    return ressource.prix_paye


def _marquer_paye(ressource) -> None:
    ressource.paiement_confirme = True
    if isinstance(ressource, DemandeActeAcademique):
        ressource.statut = StatutDemandeActe.EN_TRAITEMENT
    elif isinstance(ressource, OffreMicroJob):
        ressource.statut = StatutOffreMicroJob.OUVERTE
    elif isinstance(ressource, TransactionMarketplace):
        ressource.statut = StatutTransactionMarketplace.PAIEMENT_CONFIRME


# `partnerId` transmis au widget Kkiapay par le frontend (KkiapayButton) sous la forme
# "<type>:<id>" puis renvoye tel quel dans le webhook : c'est le payeur lui-meme qui
# designe la ressource qu'il paie. Un identifiant de transaction intercepte ne peut donc
# plus etre rattache a la ressource d'un tiers via `.../paiement/amorcer`.
_MODELES_PAR_TYPE = {
    "acte": DemandeActeAcademique,
    "ticket_transport": TicketTransport,
    "ticket_cantine": TicketCantine,
    "billet": BilletEvenement,
    "offre_micro_job": OffreMicroJob,
    "transaction_marketplace": TransactionMarketplace,
}


def _ressource_par_partner_id(db: Session, partner_id: str | None):
    if not partner_id or ":" not in partner_id:
        return None
    type_ressource, identifiant = partner_id.split(":", 1)
    modele = _MODELES_PAR_TYPE.get(type_ressource)
    return db.get(modele, identifiant) if modele is not None else None


def _ressource_par_transaction(db: Session, transaction_id: str):
    """Repli pour les paiements amorces avant l'introduction de `partnerId`."""
    for modele in _MODELES_PAR_TYPE.values():
        ressource = db.query(modele).filter(modele.kkiapay_transaction_id == transaction_id).first()
        if ressource is not None:
            return ressource
    return None


def _detacher_des_autres_ressources(db: Session, transaction_id: str, ressource) -> None:
    """Le `partnerId` fait foi : si ce transactionId avait ete rattache (via `amorcer`) a
    une autre ressource - erreur de manipulation ou tentative de detournement - ce
    rattachement est defait, sans jamais la confirmer."""
    for modele in _MODELES_PAR_TYPE.values():
        for autre in db.query(modele).filter(modele.kkiapay_transaction_id == transaction_id).all():
            if autre is not ressource:
                logger.warning(
                    "webhook_kkiapay: transaction %s detachee de %s %s (payee pour une autre ressource).",
                    transaction_id, type(autre).__name__, autre.id,
                )
                autre.kkiapay_transaction_id = None
    db.flush()


@router.post("/paiements/webhook/kkiapay", include_in_schema=False)
def webhook_kkiapay(
    payload: KkiapayWebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
    files_client: LuluFilesClient = Depends(get_files_client),
    x_kkiapay_secret: str | None = Header(default=None),
) -> dict:
    """URL UNIQUE et fixe pour TOUT le compte Kkiapay de LuluSchools. Verifie le secret
    partage (KKIAPAY_SECRET) renvoye dans l'en-tete x-kkiapay-secret, retrouve la ressource
    payee (par `partnerId`, a defaut par l'identifiant de transaction rattache) et ne la
    confirme que si le montant reellement paye correspond a son prix."""
    if not x_kkiapay_secret or not hmac.compare_digest(x_kkiapay_secret, settings.kkiapay_secret):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "secret_invalide", "Secret webhook invalide.")

    if payload.event != "transaction.success" or not payload.isPaymentSucces:
        return {"ok": True}

    ressource = _ressource_par_partner_id(db, payload.partnerId)
    if ressource is None:
        if payload.partnerId:
            logger.warning("webhook_kkiapay: partnerId %r inconnu (transaction %s).", payload.partnerId, payload.transactionId)
            return {"ok": True}
        ressource = _ressource_par_transaction(db, payload.transactionId)
    if ressource is None or not _en_attente(ressource):
        return {"ok": True}

    prix = _prix_attendu(db, ressource)
    if not _montant_correspond(prix, payload.amount):
        logger.warning(
            "webhook_kkiapay: montant recu (%s) different du prix attendu (%s) pour %s %s - paiement refuse.",
            payload.amount, prix, type(ressource).__name__, ressource.id,
        )
        return {"ok": True}
    _detacher_des_autres_ressources(db, payload.transactionId, ressource)
    ressource.kkiapay_transaction_id = payload.transactionId
    _marquer_paye(ressource)
    db.commit()
    if isinstance(ressource, DemandeActeAcademique):
        # Acte standard : genere et livre des le paiement, sans intervention de l'A+.
        background_tasks.add_task(livrer_en_arriere_plan, session_factory, ressource.id, files_client)
    return {"ok": True}
