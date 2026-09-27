from datetime import date, datetime, timedelta, timezone

from sqlalchemy import or_

# Une place reservee mais non payee n'est retenue que pendant ce delai : au-dela, elle
# ne compte plus dans la capacite (sinon quelques comptes pourraient bloquer une ligne,
# un service de cantine ou un evenement entier sans jamais payer).
DUREE_RETENUE_SANS_PAIEMENT = timedelta(minutes=30)

# Republique du Benin : UTC+1, sans heure d'ete.
FUSEAU_BENIN = timezone(timedelta(hours=1))


def aujourdhui_benin() -> date:
    return datetime.now(FUSEAU_BENIN).date()


def filtre_place_occupee(modele):
    """Condition SQL : place payee, ou reservee depuis moins de DUREE_RETENUE_SANS_PAIEMENT."""
    limite = datetime.now(timezone.utc) - DUREE_RETENUE_SANS_PAIEMENT
    return or_(modele.paiement_confirme.is_(True), modele.created_at >= limite)
