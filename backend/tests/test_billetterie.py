from datetime import datetime, timedelta, timezone

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


def _creer_evenement(client, ctx, capacite=10, prix=1000, date_heure=None):
    date_heure = date_heure or (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    return client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/evenements",
        json={
            "titre": "Kermesse",
            "description": "Fete de fin d'annee",
            "lieu": "Cour de l'ecole",
            "date_heure": date_heure,
            "capacite_max": capacite,
            "prix_billet": prix,
        },
        headers=ctx["admin_headers"],
    ).json()


def test_parcours_billet_payant_achat_paiement_validation(client, classe_avec_enseignant_et_eleve, kkiapay_secret):
    ctx = classe_avec_enseignant_et_eleve
    evenement = _creer_evenement(client, ctx)

    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]
    client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "evenement", "evenement_id": evenement["id"]},
        headers=ctx["admin_headers"],
    )

    billet = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["eleve_headers"]).json()
    assert billet["statut"] == "achete"
    assert billet["paiement_confirme"] is False

    refus = client.post(f"/api/v1/billets/{billet['id']}/valider", headers=ctx["enseignant_headers"])
    assert refus.status_code == 409

    client.post(
        f"/api/v1/billets/{billet['id']}/paiement/amorcer",
        json={"transaction_id": "tx-billet-1"},
        headers=ctx["eleve_headers"],
    )
    _payer_via_webhook(client, "tx-billet-1", kkiapay_secret)

    validation = client.post(f"/api/v1/billets/{billet['id']}/valider", headers=ctx["enseignant_headers"])
    assert validation.status_code == 200
    assert validation.json()["statut"] == "valide"


def test_billet_gratuit_est_utilisable_sans_paiement(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    evenement = _creer_evenement(client, ctx, prix=0)
    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]
    client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "evenement", "evenement_id": evenement["id"]},
        headers=ctx["admin_headers"],
    )

    billet = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["eleve_headers"]).json()
    assert billet["paiement_confirme"] is True

    validation = client.post(f"/api/v1/billets/{billet['id']}/valider", headers=ctx["enseignant_headers"])
    assert validation.status_code == 200


def test_capacite_evenement_refuse_au_dela(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    evenement = _creer_evenement(client, ctx, capacite=1, prix=0)

    premier = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["eleve_headers"])
    assert premier.status_code == 201
    second = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["enseignant_headers"])
    assert second.status_code == 409


def test_annulation_evenement_rembourse_tous_les_billets(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    evenement = _creer_evenement(client, ctx, capacite=5, prix=0)
    billet_eleve = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["eleve_headers"]).json()
    billet_enseignant = client.post(
        f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["enseignant_headers"]
    ).json()

    annulation = client.post(f"/api/v1/evenements/{evenement['id']}/annuler", headers=ctx["admin_headers"])
    assert annulation.status_code == 200
    assert annulation.json()["statut"] == "annule"

    assert client.get("/api/v1/mes-billets", headers=ctx["eleve_headers"]).json()[0]["statut"] == "rembourse"
    assert client.get("/api/v1/mes-billets", headers=ctx["enseignant_headers"]).json()[0]["statut"] == "rembourse"

    # Un evenement annule n'accepte plus de nouveaux achats.
    refus = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["eleve_headers"])
    assert refus.status_code == 409


def test_parrain_designe_peut_gerer_l_evenement_sans_etre_admin(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    evenement = _creer_evenement(client, ctx, prix=0)
    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]

    refus_avant = client.post(f"/api/v1/evenements/{evenement['id']}/annuler", headers=ctx["enseignant_headers"])
    assert refus_avant.status_code == 403

    designation = client.post(
        f"/api/v1/evenements/{evenement['id']}/parrain",
        json={"utilisateur_id": enseignant_id},
        headers=ctx["admin_headers"],
    )
    assert designation.status_code == 200
    assert designation.json()["parrain_utilisateur_id"] == enseignant_id

    annulation = client.post(f"/api/v1/evenements/{evenement['id']}/annuler", headers=ctx["enseignant_headers"])
    assert annulation.status_code == 200


def test_remboursement_billet_refuse_apres_le_delai(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    proche = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()
    evenement = _creer_evenement(client, ctx, prix=0, date_heure=proche)
    billet = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=ctx["eleve_headers"]).json()

    remboursement = client.post(f"/api/v1/billets/{billet['id']}/rembourser", headers=ctx["eleve_headers"])
    assert remboursement.status_code == 409
    assert remboursement.json()["error"]["code"] == "delai_depasse"
