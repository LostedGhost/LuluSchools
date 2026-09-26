import io
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


def _creer_eleve_dans_classe(client, fake_email_client, classe_id, admin_headers, *, email, date_naissance):
    tuteur_payload = {"nom": "Zannou", "prenom": "Parent", "email": email, "mot_de_passe": "Password1"}
    client.post("/api/v1/auth/tuteurs", json=tuteur_payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == email)
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": email, "code": code})
    login_tuteur = client.post(
        "/api/v1/auth/login", json={"identifiant": email, "mot_de_passe": "Password1"}
    ).json()
    tuteur_headers = {"Authorization": f"Bearer {login_tuteur['access_token']}"}

    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Eleve",
            "prenom": email.split(".")[0].capitalize(),
            "date_naissance": date_naissance,
            "classe_id": classe_id,
            "consentement_parental_donne": True,
        },
        headers=tuteur_headers,
    ).json()
    client.post(f"/api/v1/inscriptions/{inscription['id']}/valider", headers=admin_headers)
    identifiants = next(
        m for m in fake_email_client.sent if "login_id" in m and m["to_email"] == email
    )
    login_eleve = client.post(
        "/api/v1/auth/login",
        json={"identifiant": identifiants["login_id"], "mot_de_passe": identifiants["mot_de_passe"]},
    ).json()
    eleve_headers = {"Authorization": f"Bearer {login_eleve['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": identifiants["mot_de_passe"], "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=eleve_headers,
    )
    return eleve_headers


@pytest.fixture()
def marketplace_ctx(client, fake_email_client, admin_ministeriel_headers):
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "College Test Marketplace",
            "type": "ES",
            "statut": "public",
            "admin": {"nom": "Adjovi", "prenom": "Rachidi", "email": "rachidi.adjovi.marketplace@example.com"},
            "latitude": 6.4,
            "longitude": 2.4,
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(
        m["mot_de_passe"]
        for m in fake_email_client.sent
        if m.get("to_email") == "rachidi.adjovi.marketplace@example.com"
    )
    login_admin = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "rachidi.adjovi.marketplace@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    admin_headers = {"Authorization": f"Bearer {login_admin['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mot_de_passe_temp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=admin_headers,
    )

    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "6eme", "capacite": 3, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    ).json()

    vendeur_headers = _creer_eleve_dans_classe(
        client,
        fake_email_client,
        classe["id"],
        admin_headers,
        email="vendeur.marketplace@example.com",
        date_naissance="2009-01-01",
    )
    acheteur_headers = _creer_eleve_dans_classe(
        client,
        fake_email_client,
        classe["id"],
        admin_headers,
        email="acheteur.marketplace@example.com",
        date_naissance="2008-06-15",
    )
    mineur_headers = _creer_eleve_dans_classe(
        client,
        fake_email_client,
        classe["id"],
        admin_headers,
        email="mineur.marketplace@example.com",
        date_naissance="2013-01-01",
    )

    return {
        "etablissement": etablissement,
        "admin_headers": admin_headers,
        "vendeur_headers": vendeur_headers,
        "acheteur_headers": acheteur_headers,
        "mineur_headers": mineur_headers,
    }


def _creer_annonce(client, headers, etablissement_id, **overrides):
    payload = {
        "titre": "Cartable bleu",
        "description": "Bon etat, peu servi",
        "categorie": "fournitures_scolaires",
        "etat": "bon_etat",
        "prix": "5000",
    }
    payload.update(overrides)
    return client.post(
        f"/api/v1/etablissements/{etablissement_id}/marketplace/annonces",
        data=payload,
        files=[("photos", ("photo.jpg", io.BytesIO(b"contenu-image"), "image/jpeg"))],
        headers=headers,
    )


def test_creer_annonce_sans_photo_refusee(marketplace_ctx, client):
    ctx = marketplace_ctx
    response = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/marketplace/annonces",
        data={
            "titre": "Cartable bleu",
            "description": "Bon etat",
            "categorie": "fournitures_scolaires",
            "etat": "bon_etat",
            "prix": "5000",
        },
        headers=ctx["vendeur_headers"],
    )
    assert response.status_code == 422


def test_creer_annonce_prix_invalide_refuse(marketplace_ctx, client):
    ctx = marketplace_ctx
    response = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"], prix="0")
    assert response.status_code == 422


def test_creer_annonce_refusee_pour_un_mineur_de_moins_de_16_ans(marketplace_ctx, client):
    ctx = marketplace_ctx
    response = _creer_annonce(client, ctx["mineur_headers"], ctx["etablissement"]["id"])
    assert response.status_code == 403


def test_annonce_reservee_a_son_propre_etablissement(marketplace_ctx, client, classe_avec_enseignant_et_eleve):
    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"]).json()

    autre_etablissement_eleve = classe_avec_enseignant_et_eleve["eleve_headers"]
    refus = client.get(f"/api/v1/marketplace/annonces/{annonce['id']}", headers=autre_etablissement_eleve)
    assert refus.status_code == 403

    ok = client.get(f"/api/v1/marketplace/annonces/{annonce['id']}", headers=ctx["acheteur_headers"])
    assert ok.status_code == 200
    assert len(ok.json()["photos"]) == 1


def test_vendeur_ne_peut_pas_acheter_sa_propre_annonce(marketplace_ctx, client):
    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"]).json()
    refus = client.post(f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["vendeur_headers"])
    assert refus.status_code == 409


def test_parcours_complet_vente_avec_sequestre(marketplace_ctx, client, kkiapay_secret):
    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"], prix="7500").json()

    transaction = client.post(
        f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["acheteur_headers"]
    ).json()
    assert transaction["statut"] == "en_attente_paiement"

    annonce_reservee = client.get(
        f"/api/v1/marketplace/annonces/{annonce['id']}", headers=ctx["acheteur_headers"]
    ).json()
    assert annonce_reservee["statut"] == "reservee"

    encore_dispo = client.post(f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["mineur_headers"])
    assert encore_dispo.status_code in (403, 409)  # mineur refuse de toute facon avant meme le statut

    client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{transaction['id']}"},
        headers=ctx["acheteur_headers"],
    )
    _payer_via_webhook(client, f"tx-{transaction['id']}", kkiapay_secret)

    remise = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/declarer-remise", headers=ctx["vendeur_headers"]
    )
    assert remise.status_code == 200
    assert remise.json()["statut"] == "remise_declaree"

    confirmation = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/confirmer", headers=ctx["acheteur_headers"]
    )
    assert confirmation.status_code == 200
    assert confirmation.json()["statut"] == "confirmee"

    reversement = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/reverser-vendeur",
        json={"reference_paiement": "MOMO-REF-MKT-1"},
        headers=ctx["admin_headers"],
    )
    assert reversement.status_code == 200
    assert reversement.json()["statut"] == "finalisee"

    annonce_finale = client.get(
        f"/api/v1/marketplace/annonces/{annonce['id']}", headers=ctx["acheteur_headers"]
    ).json()
    assert annonce_finale["statut"] == "vendue"

    historique_vendeur = client.get("/api/v1/mes-transactions-marketplace", headers=ctx["vendeur_headers"]).json()
    assert len(historique_vendeur) == 1
    historique_acheteur = client.get("/api/v1/mes-transactions-marketplace", headers=ctx["acheteur_headers"]).json()
    assert len(historique_acheteur) == 1


def test_annuler_transaction_avant_paiement(marketplace_ctx, client):
    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"]).json()
    transaction = client.post(
        f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["acheteur_headers"]
    ).json()

    annulation = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/annuler", headers=ctx["acheteur_headers"]
    )
    assert annulation.status_code == 200
    assert annulation.json()["statut"] == "annulee"

    annonce_a_jour = client.get(
        f"/api/v1/marketplace/annonces/{annonce['id']}", headers=ctx["vendeur_headers"]
    ).json()
    assert annonce_a_jour["statut"] == "disponible"


def test_contestation_acceptee_rembourse_et_reannonce_disponible(marketplace_ctx, client, kkiapay_secret):
    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"]).json()
    transaction = client.post(
        f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["acheteur_headers"]
    ).json()
    client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{transaction['id']}"},
        headers=ctx["acheteur_headers"],
    )
    _payer_via_webhook(client, f"tx-{transaction['id']}", kkiapay_secret)
    client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/declarer-remise", headers=ctx["vendeur_headers"]
    )

    contestation = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/contester",
        json={"motif": "Article non conforme a la description"},
        headers=ctx["acheteur_headers"],
    )
    assert contestation.status_code == 201

    sans_motif = client.post(
        f"/api/v1/marketplace/contestations/{contestation.json()['id']}/decision",
        json={"decision": "rejetee"},
        headers=ctx["admin_headers"],
    )
    assert sans_motif.status_code == 422

    decision = client.post(
        f"/api/v1/marketplace/contestations/{contestation.json()['id']}/decision",
        json={"decision": "acceptee"},
        headers=ctx["admin_headers"],
    )
    assert decision.status_code == 200

    annonce_a_jour = client.get(
        f"/api/v1/marketplace/annonces/{annonce['id']}", headers=ctx["vendeur_headers"]
    ).json()
    assert annonce_a_jour["statut"] == "disponible"

    transaction_a_jour = client.get("/api/v1/mes-transactions-marketplace", headers=ctx["acheteur_headers"]).json()[0]
    assert transaction_a_jour["statut"] == "remboursee"


def test_confirmation_tacite_apres_le_delai(marketplace_ctx, client, kkiapay_secret, db_session):
    from app.modules.marketplace.models import TransactionMarketplace

    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"]).json()
    transaction = client.post(
        f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["acheteur_headers"]
    ).json()
    client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{transaction['id']}"},
        headers=ctx["acheteur_headers"],
    )
    _payer_via_webhook(client, f"tx-{transaction['id']}", kkiapay_secret)
    client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/declarer-remise", headers=ctx["vendeur_headers"]
    )

    transaction_db = db_session.get(TransactionMarketplace, transaction["id"])
    transaction_db.date_limite_confirmation = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    refus_contestation = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/contester",
        json={"motif": "Trop tard"},
        headers=ctx["acheteur_headers"],
    )
    assert refus_contestation.status_code == 409

    transaction_a_jour = client.get("/api/v1/mes-transactions-marketplace", headers=ctx["acheteur_headers"]).json()[0]
    assert transaction_a_jour["statut"] == "confirmee"


def test_signalement_et_traitement(marketplace_ctx, client):
    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"]).json()

    signalement = client.post(
        f"/api/v1/marketplace/annonces/{annonce['id']}/signaler", headers=ctx["acheteur_headers"]
    )
    assert signalement.status_code == 201

    en_attente = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/marketplace/signalements", headers=ctx["admin_headers"]
    ).json()
    assert len(en_attente) == 1

    traitement = client.post(
        f"/api/v1/marketplace/signalements/{en_attente[0]['id']}/traiter",
        json={"decision": "Annonce conforme, aucune action"},
        headers=ctx["admin_headers"],
    )
    assert traitement.status_code == 200
    assert traitement.json()["traite"] is True


def test_retrait_par_le_vendeur_avant_reservation(marketplace_ctx, client):
    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"]).json()

    retrait = client.delete(f"/api/v1/marketplace/annonces/{annonce['id']}", headers=ctx["vendeur_headers"])
    assert retrait.status_code == 204

    refus_reservation = client.post(
        f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["acheteur_headers"]
    )
    assert refus_reservation.status_code == 409


def test_retrait_par_admin_rembourse_la_transaction_en_cours(marketplace_ctx, client, kkiapay_secret):
    ctx = marketplace_ctx
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"]).json()
    transaction = client.post(
        f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["acheteur_headers"]
    ).json()
    client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{transaction['id']}"},
        headers=ctx["acheteur_headers"],
    )
    _payer_via_webhook(client, f"tx-{transaction['id']}", kkiapay_secret)

    retrait = client.post(
        f"/api/v1/marketplace/annonces/{annonce['id']}/retirer",
        json={"motif": "Objet interdit sur la plateforme"},
        headers=ctx["admin_headers"],
    )
    assert retrait.status_code == 200
    assert retrait.json()["statut"] == "retiree"

    transaction_a_jour = client.get("/api/v1/mes-transactions-marketplace", headers=ctx["acheteur_headers"]).json()[0]
    assert transaction_a_jour["statut"] == "remboursee"
