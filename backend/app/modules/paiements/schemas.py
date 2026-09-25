from pydantic import BaseModel, ConfigDict


class AmorcerPaiementRequest(BaseModel):
    """Partage par tous les flux payants (actes, tickets, billetterie, micro-jobs) :
    le client appelle systematiquement `.../paiement/amorcer` juste apres avoir obtenu
    un transactionId du widget Kkiapay, pour associer cette transaction a sa ressource
    AVANT que le webhook global ne confirme le paiement."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str


class KkiapayWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Kkiapay envoie d'autres champs (amount, fees, method...)

    transactionId: str
    isPaymentSucces: bool
    event: str
