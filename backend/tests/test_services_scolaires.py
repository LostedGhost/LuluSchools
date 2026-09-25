from datetime import date, timedelta

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


def test_parcours_ticket_transport_achat_paiement_validation(client, classe_avec_enseignant_et_eleve, kkiapay_secret):
    ctx = classe_avec_enseignant_et_eleve
    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]
    client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "transport"},
        headers=ctx["admin_headers"],
    )
    ligne = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/lignes-transport",
        json={"nom": "Ligne A", "prix": 200, "capacite_par_trajet": 1},
        headers=ctx["admin_headers"],
    ).json()

    demain = (date.today() + timedelta(days=5)).isoformat()
    ticket = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets",
        json={"date_trajet": demain},
        headers=ctx["eleve_headers"],
    ).json()
    assert ticket["statut"] == "achete"
    assert ticket["paiement_confirme"] is False

    # Refuse de valider tant que le paiement n'est pas confirme.
    refus = client.post(f"/api/v1/tickets-transport/{ticket['id']}/valider", headers=ctx["enseignant_headers"])
    assert refus.status_code == 409

    client.post(
        f"/api/v1/tickets-transport/{ticket['id']}/paiement/amorcer",
        json={"transaction_id": "tx-transport-1"},
        headers=ctx["eleve_headers"],
    )
    _payer_via_webhook(client, "tx-transport-1", kkiapay_secret)

    validation = client.post(f"/api/v1/tickets-transport/{ticket['id']}/valider", headers=ctx["enseignant_headers"])
    assert validation.status_code == 200
    assert validation.json()["statut"] == "valide"

    # Un ticket deja valide ne peut plus etre valide une seconde fois, ni rembourse.
    revalidation = client.post(f"/api/v1/tickets-transport/{ticket['id']}/valider", headers=ctx["enseignant_headers"])
    assert revalidation.status_code == 409
    remboursement = client.post(f"/api/v1/tickets-transport/{ticket['id']}/rembourser", headers=ctx["eleve_headers"])
    assert remboursement.status_code == 409


def test_capacite_ligne_transport_refuse_au_dela(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    ligne = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/lignes-transport",
        json={"nom": "Ligne pleine", "prix": 100, "capacite_par_trajet": 1},
        headers=ctx["admin_headers"],
    ).json()
    demain = (date.today() + timedelta(days=5)).isoformat()

    premier = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets",
        json={"date_trajet": demain},
        headers=ctx["eleve_headers"],
    )
    assert premier.status_code == 201

    eleve_utilisateur_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    second = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets",
        json={"date_trajet": demain, "eleve_utilisateur_id": eleve_utilisateur_id},
        headers=ctx["tuteur_headers"],
    )
    assert second.status_code == 409


def test_tuteur_peut_acheter_pour_son_enfant_et_consulter(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    ligne = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/lignes-transport",
        json={"nom": "Ligne B", "prix": 150, "capacite_par_trajet": 5},
        headers=ctx["admin_headers"],
    ).json()
    eleve_utilisateur_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    demain = (date.today() + timedelta(days=5)).isoformat()

    sans_id = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets",
        json={"date_trajet": demain},
        headers=ctx["tuteur_headers"],
    )
    assert sans_id.status_code == 422

    ticket = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets",
        json={"date_trajet": demain, "eleve_utilisateur_id": eleve_utilisateur_id},
        headers=ctx["tuteur_headers"],
    ).json()
    assert ticket["utilisateur_id"] == eleve_utilisateur_id

    mes_tickets_tuteur = client.get("/api/v1/mes-tickets-transport", headers=ctx["tuteur_headers"])
    assert len(mes_tickets_tuteur.json()) == 1
    mes_tickets_eleve = client.get("/api/v1/mes-tickets-transport", headers=ctx["eleve_headers"])
    assert len(mes_tickets_eleve.json()) == 1


def test_remboursement_refuse_apres_le_delai(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    ligne = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/lignes-transport",
        json={"nom": "Ligne C", "prix": 100, "capacite_par_trajet": 5},
        headers=ctx["admin_headers"],
    ).json()
    aujourdhui = date.today().isoformat()
    ticket = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets",
        json={"date_trajet": aujourdhui},
        headers=ctx["eleve_headers"],
    ).json()

    remboursement = client.post(f"/api/v1/tickets-transport/{ticket['id']}/rembourser", headers=ctx["eleve_headers"])
    assert remboursement.status_code == 409
    assert remboursement.json()["error"]["code"] == "delai_depasse"


def test_seul_le_controleur_designe_peut_valider(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    ligne = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/lignes-transport",
        json={"nom": "Ligne D", "prix": 100, "capacite_par_trajet": 5},
        headers=ctx["admin_headers"],
    ).json()
    demain = (date.today() + timedelta(days=5)).isoformat()
    ticket = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets",
        json={"date_trajet": demain},
        headers=ctx["eleve_headers"],
    ).json()

    refus = client.post(f"/api/v1/tickets-transport/{ticket['id']}/valider", headers=ctx["enseignant_headers"])
    assert refus.status_code == 403


def test_parcours_ticket_cantine(client, classe_avec_enseignant_et_eleve, kkiapay_secret):
    ctx = classe_avec_enseignant_et_eleve
    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]
    client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "cantine"},
        headers=ctx["admin_headers"],
    )
    type_repas = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-repas-cantine",
        json={"nom": "Menu du jour", "prix": 500, "capacite_par_jour": 2},
        headers=ctx["admin_headers"],
    ).json()

    demain = (date.today() + timedelta(days=5)).isoformat()
    ticket = client.post(
        f"/api/v1/types-repas-cantine/{type_repas['id']}/tickets",
        json={"date_service": demain},
        headers=ctx["eleve_headers"],
    ).json()

    client.post(
        f"/api/v1/tickets-cantine/{ticket['id']}/paiement/amorcer",
        json={"transaction_id": "tx-cantine-1"},
        headers=ctx["eleve_headers"],
    )
    _payer_via_webhook(client, "tx-cantine-1", kkiapay_secret)

    validation = client.post(f"/api/v1/tickets-cantine/{ticket['id']}/valider", headers=ctx["enseignant_headers"])
    assert validation.status_code == 200
    assert validation.json()["statut"] == "valide"

    historique = client.get("/api/v1/mes-tickets-cantine", headers=ctx["eleve_headers"])
    assert len(historique.json()) == 1
