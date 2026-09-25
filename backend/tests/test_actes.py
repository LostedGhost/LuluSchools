def test_reclamation_gratuite_va_directement_en_traitement(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    response = client.post(
        "/api/v1/demandes-actes",
        json={"est_reclamation": True, "reference_evaluation": "devoir-123", "motif": "Erreur de note"},
        headers=ctx["eleve_headers"],
    )
    assert response.status_code == 201
    assert response.json()["statut"] == "en_traitement"
    assert response.json()["paiement_confirme"] is True


def test_acte_payant_attend_le_paiement_avant_traitement(client, classe_avec_enseignant_et_eleve, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "kkiapay_secret", "secret-de-test")
    ctx = classe_avec_enseignant_et_eleve
    type_acte = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-actes",
        json={"nom": "Attestation de succes", "prix": 1000, "pieces_requises": "CIP, acte de naissance"},
        headers=ctx["admin_headers"],
    ).json()

    demande = client.post(
        "/api/v1/demandes-actes",
        json={"type_acte_id": type_acte["id"]},
        headers=ctx["eleve_headers"],
    ).json()
    assert demande["statut"] == "soumise"
    assert demande["paiement_confirme"] is False

    refus_traitement = client.post(
        f"/api/v1/demandes-actes/{demande['id']}/traiter",
        json={"decision": "acceptee"},
        headers=ctx["admin_headers"],
    )
    assert refus_traitement.status_code == 409

    # Le frontend associe la transaction Kkiapay a la demande des l'obtention du
    # transactionId (widget cote client), avant meme la confirmation par webhook.
    amorce = client.post(
        f"/api/v1/demandes-actes/{demande['id']}/paiement/amorcer",
        json={"transaction_id": "kkiapay-tx-1"},
        headers=ctx["eleve_headers"],
    )
    assert amorce.status_code == 200

    webhook_mauvais_secret = client.post(
        "/api/v1/paiements/webhook/kkiapay",
        json={"transactionId": "kkiapay-tx-1", "isPaymentSucces": True, "event": "transaction.success"},
        headers={"x-kkiapay-secret": "mauvais-secret"},
    )
    assert webhook_mauvais_secret.status_code == 401

    webhook = client.post(
        "/api/v1/paiements/webhook/kkiapay",
        json={"transactionId": "kkiapay-tx-1", "isPaymentSucces": True, "event": "transaction.success"},
        headers={"x-kkiapay-secret": "secret-de-test"},
    )
    assert webhook.status_code == 200

    demande_a_jour = client.get(f"/api/v1/demandes-actes/{demande['id']}", headers=ctx["admin_headers"])
    assert demande_a_jour.json()["statut"] == "en_traitement"
    assert demande_a_jour.json()["paiement_confirme"] is True

    traitement = client.post(
        f"/api/v1/demandes-actes/{demande['id']}/traiter",
        json={"decision": "acceptee"},
        headers=ctx["admin_headers"],
    )
    assert traitement.status_code == 200
    assert traitement.json()["statut"] == "acceptee"


def test_type_acte_gratuit_va_directement_en_traitement(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    type_acte = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-actes",
        json={"nom": "Diplome", "prix": 0, "pieces_requises": "Aucune"},
        headers=ctx["admin_headers"],
    ).json()

    demande = client.post(
        "/api/v1/demandes-actes", json={"type_acte_id": type_acte["id"]}, headers=ctx["eleve_headers"]
    ).json()
    assert demande["statut"] == "en_traitement"


def test_tuteur_peut_soumettre_pour_son_enfant(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_utilisateur_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    sans_eleve_id = client.post(
        "/api/v1/demandes-actes",
        json={"est_reclamation": True, "reference_evaluation": "devoir-123"},
        headers=ctx["tuteur_headers"],
    )
    assert sans_eleve_id.status_code == 422

    response = client.post(
        "/api/v1/demandes-actes",
        json={
            "est_reclamation": True,
            "reference_evaluation": "devoir-123",
            "eleve_utilisateur_id": eleve_utilisateur_id,
        },
        headers=ctx["tuteur_headers"],
    )
    assert response.status_code == 201


def test_rejet_demande_acte_requiert_un_motif(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    demande = client.post(
        "/api/v1/demandes-actes",
        json={"est_reclamation": True, "reference_evaluation": "devoir-123"},
        headers=ctx["eleve_headers"],
    ).json()

    sans_motif = client.post(
        f"/api/v1/demandes-actes/{demande['id']}/traiter", json={"decision": "rejetee"}, headers=ctx["admin_headers"]
    )
    assert sans_motif.status_code == 422

    avec_motif = client.post(
        f"/api/v1/demandes-actes/{demande['id']}/traiter",
        json={"decision": "rejetee", "motif_rejet": "Reclamation non fondee"},
        headers=ctx["admin_headers"],
    )
    assert avec_motif.status_code == 200
    assert avec_motif.json()["statut"] == "rejetee"
