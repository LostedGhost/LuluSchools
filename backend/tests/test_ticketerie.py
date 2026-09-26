from datetime import date, datetime, timedelta, timezone

import pytest


@pytest.fixture()
def kkiapay_secret(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "kkiapay_secret", "secret-de-test")
    return "secret-de-test"


def _payer_via_webhook(client, transaction_id, secret):
    return client.post(
        "/api/v1/paiements/webhook/kkiapay",
        json={"transactionId": transaction_id, "isPaymentSucces": True, "event": "transaction.success"},
        headers={"x-kkiapay-secret": secret},
    )


def test_pdf_ticket_transport_avec_qr(client, classe_avec_enseignant_et_eleve, kkiapay_secret):
    """UC-54/68 (lot admin etablissement) : le PDF genere est bien un PDF valide,
    accessible au proprietaire du ticket."""
    ctx = classe_avec_enseignant_et_eleve
    ligne = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/lignes-transport",
        json={"nom": "Ligne A", "prix": 200, "capacite_par_trajet": 5},
        headers=ctx["admin_headers"],
    ).json()
    demain = (date.today() + timedelta(days=5)).isoformat()
    ticket = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets", json={"date_trajet": demain}, headers=ctx["eleve_headers"]
    ).json()

    pdf = client.get(f"/api/v1/tickets-transport/{ticket['id']}/pdf", headers=ctx["eleve_headers"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"

    # Le tuteur de l'eleve proprietaire est lui aussi habilite (meme regle que
    # obtenir_ticket_transport, reutilisee telle quelle par le nouvel endpoint PDF).
    pdf_tuteur = client.get(f"/api/v1/tickets-transport/{ticket['id']}/pdf", headers=ctx["tuteur_headers"])
    assert pdf_tuteur.status_code == 200


def test_pdf_ticket_cantine_avec_qr(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    type_repas = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-repas-cantine",
        json={"nom": "Dejeuner", "prix": 500, "capacite_par_jour": 20},
        headers=ctx["admin_headers"],
    ).json()
    demain = (date.today() + timedelta(days=2)).isoformat()
    ticket = client.post(
        f"/api/v1/types-repas-cantine/{type_repas['id']}/tickets",
        json={"date_service": demain},
        headers=ctx["eleve_headers"],
    ).json()

    pdf = client.get(f"/api/v1/tickets-cantine/{ticket['id']}/pdf", headers=ctx["eleve_headers"])
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def _creer_evenement(client, ctx, date_heure=None):
    date_heure = date_heure or (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    return client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/evenements",
        json={
            "titre": "Kermesse",
            "description": "Fete de fin d'annee",
            "lieu": "Cour de l'ecole",
            "date_heure": date_heure,
            "capacite_max": 10,
            "prix_billet": 0,
        },
        headers=ctx["admin_headers"],
    ).json()


def test_pdf_billet_evenement_avec_qr(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    evenement = _creer_evenement(client, ctx)
    billet = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["eleve_headers"]).json()

    pdf = client.get(f"/api/v1/billets/{billet['id']}/pdf", headers=ctx["eleve_headers"])
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"

    refus = client.get(f"/api/v1/billets/{billet['id']}/pdf", headers=ctx["tuteur_headers"])
    assert refus.status_code == 403


def test_jeton_ticket_encode_et_decode_correctement():
    from app.modules.ticketerie.generation import decoder_jeton_ticket, jeton_ticket

    jeton = jeton_ticket("transport", "abc-123")
    assert decoder_jeton_ticket(jeton) == ("transport", "abc-123")
