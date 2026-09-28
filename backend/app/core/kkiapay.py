"""Client Kkiapay minimal : remboursement automatique d'une transaction.

Meme appel que le SDK officiel (github.com/kkiapay/kkiapay-python, core.py :
refund_transaction) : POST /api/v1/transactions/revert, en-tetes X-API-KEY /
X-PRIVATE-KEY / X-SECRET-KEY. Kkiapay ne propose en revanche AUCUN virement vers un
tiers (son "payout" ne fait que reverser le solde du marchand vers SON propre compte) :
les reversements aux vendeurs et prestataires restent un virement Mobile Money humain,
simplement regroupe par beneficiaire (voir marketplace et micro_jobs).
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class KkiapayClient:
    def __init__(self) -> None:
        self.actif = bool(settings.kkiapay_public_key and settings.kkiapay_private_key and settings.kkiapay_secret)
        base = "https://api-sandbox.kkiapay.me" if settings.kkiapay_sandbox else "https://api.kkiapay.me"
        self._url_remboursement = f"{base}/api/v1/transactions/revert"
        self._entetes = {
            "Accept": "application/json",
            "X-SECRET-KEY": settings.kkiapay_secret,
            "X-API-KEY": settings.kkiapay_public_key,
            "X-PRIVATE-KEY": settings.kkiapay_private_key,
        }

    def rembourser(self, transaction_id: str) -> bool:
        """True si Kkiapay a accepte le remboursement ; False sinon (cles absentes, refus,
        indisponibilite) - l'appelant laisse alors le remboursement a faire a la main."""
        if not self.actif or not transaction_id:
            return False
        try:
            reponse = httpx.post(self._url_remboursement, data={"transactionId": transaction_id}, headers=self._entetes, timeout=20.0)
        except httpx.HTTPError:
            logger.warning("kkiapay: remboursement de %s impossible (reseau)", transaction_id)
            return False
        if reponse.status_code >= 400:
            logger.warning("kkiapay: remboursement de %s refuse (%s) : %s", transaction_id, reponse.status_code, reponse.text[:300])
            return False
        return True


def get_kkiapay_client() -> KkiapayClient:
    return KkiapayClient()


def rembourser(client: KkiapayClient, ressource) -> None:
    """Rembourse une ressource payee (ticket, billet, transaction, mission) et note si c'est
    fait. Sans paiement confirme, il n'y a rien a rembourser."""
    if not getattr(ressource, "paiement_confirme", False) or getattr(ressource, "remboursement_effectue", False):
        return
    ressource.remboursement_effectue = client.rembourser(ressource.kkiapay_transaction_id or "")
