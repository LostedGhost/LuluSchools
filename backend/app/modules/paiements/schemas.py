from pydantic import BaseModel, ConfigDict


class AmorcerPaiementRequest(BaseModel):
    """Partage par tous les flux payants (actes, tickets, billetterie, micro-jobs) :
    le client appelle systematiquement `.../paiement/amorcer` juste apres avoir obtenu
    un transactionId du widget Kkiapay, pour associer cette transaction a sa ressource
    AVANT que le webhook global ne confirme le paiement."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str


class KkiapayWebhookPayload(BaseModel):
    """`amount` (montant reellement paye, en FCFA - voir docs.kkiapay.me/v1/tableau-de-bord/webhook)
    est indispensable : sans verification cote serveur, un appelant peut amorcer un
    paiement bon marche puis rattacher (via `.../paiement/amorcer`) ce transactionId a
    une ressource bien plus chere - le webhook ne doit confirmer que si `amount`
    correspond au prix reel de la ressource visee (voir chaque _confirmer_* de router.py)."""

    model_config = ConfigDict(extra="ignore")  # Kkiapay envoie d'autres champs (fees, method...)

    transactionId: str
    isPaymentSucces: bool
    event: str
    amount: float
    # "<type>:<id>" transmis au widget par le frontend (voir paiements/router.py).
    partnerId: str | None = None
