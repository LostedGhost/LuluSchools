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


def _eleve_utilisateur_id(client, tuteur_headers):
    inscriptions = client.get("/api/v1/tuteurs/me/inscriptions", headers=tuteur_headers).json()
    return inscriptions[0]["eleve_utilisateur_id"]


def test_sans_plafond_configure_le_paiement_n_est_jamais_bloque(client, classe_avec_tuteur_et_etudiant):
    """UC-35.4 : opt-in strict, comportement actuel inchange par defaut."""
    ctx = classe_avec_tuteur_et_etudiant
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours de soutien", "description": "Aide aux devoirs", "prix": 5000},
        headers=ctx["eleve_headers"],
    ).json()
    amorcage = client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["eleve_headers"],
    )
    assert amorcage.status_code == 200


def test_seuil_de_validation_bloque_le_paiement_jusqu_a_decision_du_tuteur(
    client, classe_avec_tuteur_et_etudiant, kkiapay_secret
):
    ctx = classe_avec_tuteur_et_etudiant
    eleve_utilisateur_id = _eleve_utilisateur_id(client, ctx["tuteur_headers"])

    plafond = client.put(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/plafond",
        json={"seuil_validation": 2000},
        headers=ctx["tuteur_headers"],
    )
    assert plafond.status_code == 200
    assert plafond.json()["seuil_validation"] == 2000

    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours de soutien", "description": "Aide aux devoirs", "prix": 5000},
        headers=ctx["eleve_headers"],
    ).json()

    bloque = client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["eleve_headers"],
    )
    assert bloque.status_code == 409
    assert bloque.json()["error"]["code"] == "en_attente_validation_parentale"

    vue_eleve = client.get("/api/v1/coffre-fort/mes-validations-en-attente", headers=ctx["eleve_headers"]).json()
    assert len(vue_eleve) == 1
    assert vue_eleve[0]["reference_id"] == offre["id"]
    assert vue_eleve[0]["statut"] == "en_attente"

    vue_tuteur = client.get(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/validations-en-attente",
        headers=ctx["tuteur_headers"],
    ).json()
    assert len(vue_tuteur) == 1
    validation_id = vue_tuteur[0]["id"]

    encore_bloque = client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["eleve_headers"],
    )
    assert encore_bloque.status_code == 409

    approbation = client.post(
        f"/api/v1/coffre-fort/validations/{validation_id}/approuver", headers=ctx["tuteur_headers"]
    )
    assert approbation.status_code == 200
    assert approbation.json()["statut"] == "approuvee"

    amorcage_ok = client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["eleve_headers"],
    )
    assert amorcage_ok.status_code == 200
    _payer_via_webhook(client, f"tx-{offre['id']}", kkiapay_secret)
    offre_finale = client.get(f"/api/v1/micro-jobs/offres/{offre['id']}", headers=ctx["eleve_headers"]).json()
    assert offre_finale["statut"] == "ouverte"


def test_refus_du_tuteur_maintient_le_blocage_et_peut_etre_relance(
    client, classe_avec_tuteur_et_etudiant
):
    ctx = classe_avec_tuteur_et_etudiant
    eleve_utilisateur_id = _eleve_utilisateur_id(client, ctx["tuteur_headers"])
    client.put(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/plafond",
        json={"seuil_validation": 1000},
        headers=ctx["tuteur_headers"],
    )
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours de soutien", "description": "Aide aux devoirs", "prix": 5000},
        headers=ctx["eleve_headers"],
    ).json()
    client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["eleve_headers"],
    )
    validation_id = client.get(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/validations-en-attente",
        headers=ctx["tuteur_headers"],
    ).json()[0]["id"]

    refus = client.post(
        f"/api/v1/coffre-fort/validations/{validation_id}/refuser",
        json={"motif_refus": "Depense non justifiee"},
        headers=ctx["tuteur_headers"],
    )
    assert refus.status_code == 200
    assert refus.json()["statut"] == "refusee"

    toujours_bloque = client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["eleve_headers"],
    )
    assert toujours_bloque.status_code == 409

    nouvelles_validations = client.get(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/validations-en-attente",
        headers=ctx["tuteur_headers"],
    ).json()
    assert len(nouvelles_validations) == 1
    assert nouvelles_validations[0]["id"] != validation_id


def test_depassement_du_plafond_hebdomadaire_notifie_sans_jamais_bloquer(
    client, classe_avec_tuteur_et_etudiant
):
    ctx = classe_avec_tuteur_et_etudiant
    eleve_utilisateur_id = _eleve_utilisateur_id(client, ctx["tuteur_headers"])
    client.put(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/plafond",
        json={"plafond_hebdomadaire": 1000},
        headers=ctx["tuteur_headers"],
    )
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours de soutien", "description": "Aide aux devoirs", "prix": 5000},
        headers=ctx["eleve_headers"],
    ).json()

    amorcage = client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["eleve_headers"],
    )
    assert amorcage.status_code == 200

    alertes = client.get(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/alertes", headers=ctx["tuteur_headers"]
    ).json()
    assert len(alertes) == 1
    assert alertes[0]["montant_semaine"] == 5000
    assert alertes[0]["plafond"] == 1000


def test_releve_financier_agrege_les_depenses_de_l_enfant(client, classe_avec_tuteur_et_etudiant, kkiapay_secret):
    ctx = classe_avec_tuteur_et_etudiant
    eleve_utilisateur_id = _eleve_utilisateur_id(client, ctx["tuteur_headers"])
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours de soutien", "description": "Aide aux devoirs", "prix": 3000},
        headers=ctx["eleve_headers"],
    ).json()
    client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["eleve_headers"],
    )
    _payer_via_webhook(client, f"tx-{offre['id']}", kkiapay_secret)

    releve = client.get(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/releve", headers=ctx["tuteur_headers"]
    ).json()
    assert releve["depenses_micro_jobs"] == 3000
    assert releve["gains_micro_jobs"] == 0
    assert releve["solde_net"] == -3000


def test_seul_le_tuteur_de_l_enfant_peut_gerer_son_coffre_fort(client, classe_avec_enseignant_et_eleve, fake_email_client):
    ctx = classe_avec_enseignant_et_eleve
    eleve_utilisateur_id = _eleve_utilisateur_id(client, ctx["tuteur_headers"])

    autre_tuteur_payload = {
        "nom": "Sanni", "prenom": "Karim", "email": "karim.sanni.coffre-fort@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=autre_tuteur_payload)
    code = next(
        m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == autre_tuteur_payload["email"]
    )
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": autre_tuteur_payload["email"], "code": code})
    login_autre_tuteur = client.post(
        "/api/v1/auth/login",
        json={"identifiant": autre_tuteur_payload["email"], "mot_de_passe": autre_tuteur_payload["mot_de_passe"]},
    ).json()
    autre_tuteur_headers = {"Authorization": f"Bearer {login_autre_tuteur['access_token']}"}

    refus = client.put(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/coffre-fort/plafond",
        json={"seuil_validation": 1000},
        headers=autre_tuteur_headers,
    )
    assert refus.status_code == 403
