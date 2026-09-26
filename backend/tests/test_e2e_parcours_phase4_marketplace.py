"""Test de bout en bout (etape 5 de la methode lucio-dev) pour la Phase 4 : rejoue
l'enchainement REEL des UC-20 a UC-22 (annonce -> signalement traite -> reservation ->
paiement sequestre -> remise -> confirmation -> reversement au vendeur), avec les memes
objets (etablissement, classe, deux eleves >=16 ans) qui circulent d'un endpoint a
l'autre - meme principe que test_e2e_parcours_complet.py (Phase 1) et
test_e2e_parcours_phase2_3.py (Phase 2/3).

Les regles metier deja couvertes par les tests unitaires du module (annulation avant
paiement, contestation, confirmation tacite, retrait par le vendeur ou par l'A+, refus
RBAC) ne sont pas repetees ici : ce test suit le chemin nominal complet, UC-20 a UC-22.
"""

import io


def _signup_et_verifier_tuteur(client, fake_email_client, nom, prenom, email, mot_de_passe="Password1"):
    client.post(
        "/api/v1/auth/tuteurs", json={"nom": nom, "prenom": prenom, "email": email, "mot_de_passe": mot_de_passe}
    )
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == email)
    verif = client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": email, "code": code})
    assert verif.status_code == 200
    return _login(client, email, mot_de_passe)


def _login(client, identifiant, mot_de_passe):
    reponse = client.post("/api/v1/auth/login", json={"identifiant": identifiant, "mot_de_passe": mot_de_passe})
    assert reponse.status_code == 200, reponse.json()
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}, reponse.json()


def _changer_mot_de_passe(client, headers, ancien, nouveau="NouveauMdp1"):
    reponse = client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": ancien, "nouveau_mot_de_passe": nouveau},
        headers=headers,
    )
    assert reponse.status_code == 200


def _inscrire_eleve_de_16_ans_ou_plus(client, fake_email_client, admin_headers, classe_id, *, tuteur_email, date_naissance):
    tuteur_headers, _ = _signup_et_verifier_tuteur(client, fake_email_client, "Dossou", "Parent", tuteur_email)
    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Eleve", "prenom": tuteur_email.split(".")[0].capitalize(),
            "date_naissance": date_naissance, "classe_id": classe_id,
        },
        headers=tuteur_headers,
    )
    assert inscription.status_code == 201
    assert inscription.json()["statut"] == "soumise"  # >=16 ans : pas de consentement parental requis (Art. 446)
    client.post(f"/api/v1/inscriptions/{inscription.json()['id']}/valider", headers=admin_headers)
    identifiants = next(
        m for m in fake_email_client.sent if "login_id" in m and m.get("to_email") == tuteur_email
    )
    eleve_headers, _ = _login(client, identifiants["login_id"], identifiants["mot_de_passe"])
    _changer_mot_de_passe(client, eleve_headers, identifiants["mot_de_passe"])
    return eleve_headers


def _payer_via_webhook(client, transaction_id, secret):
    reponse = client.post(
        "/api/v1/paiements/webhook/kkiapay",
        json={"transactionId": transaction_id, "isPaymentSucces": True, "event": "transaction.success"},
        headers={"x-kkiapay-secret": secret},
    )
    assert reponse.status_code == 200


def test_parcours_complet_de_la_phase_4_marketplace(
    client, fake_email_client, admin_ministeriel_headers, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "kkiapay_secret", "secret-de-test-e2e-marketplace")
    secret = "secret-de-test-e2e-marketplace"

    # ---------------------------------------------------------------
    # 0. Socle : etablissement, classe, deux eleves >=16 ans inscrits et valides
    #    (vendeur et acheteur du meme etablissement, condition posee par UC-20).
    # ---------------------------------------------------------------
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Lycee Toffa 1er",
            "type": "ES",
            "statut": "public",
            "admin": {"nom": "Sagbo", "prenom": "Colette", "email": "colette.sagbo.e2e4@example.com"},
            "latitude": 6.3654,
            "longitude": 2.4183,
        },
        headers=admin_ministeriel_headers,
    )
    assert etablissement.status_code == 201
    etablissement = etablissement.json()

    mot_de_passe_admin_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "colette.sagbo.e2e4@example.com"
    )
    admin_headers, _ = _login(client, "colette.sagbo.e2e4@example.com", mot_de_passe_admin_temp)
    _changer_mot_de_passe(client, admin_headers, mot_de_passe_admin_temp)

    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "Terminale D", "capacite": 5, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    ).json()

    vendeur_headers = _inscrire_eleve_de_16_ans_ou_plus(
        client, fake_email_client, admin_headers, classe["id"],
        tuteur_email="parent.vendeur.e2e4@example.com", date_naissance="2009-02-10",
    )
    acheteur_headers = _inscrire_eleve_de_16_ans_ou_plus(
        client, fake_email_client, admin_headers, classe["id"],
        tuteur_email="parent.acheteur.e2e4@example.com", date_naissance="2008-11-20",
    )

    # ---------------------------------------------------------------
    # 1. UC-20 : le vendeur publie une annonce (au moins une photo obligatoire)
    # ---------------------------------------------------------------
    annonce = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/marketplace/annonces",
        data={
            "titre": "Calculatrice scientifique",
            "description": "Casio graph 35+, tres bon etat, pile neuve",
            "categorie": "electronique",
            "etat": "tres_bon_etat",
            "prix": "12000",
        },
        files=[("photos", ("calculatrice.jpg", io.BytesIO(b"contenu-photo"), "image/jpeg"))],
        headers=vendeur_headers,
    )
    assert annonce.status_code == 201
    annonce = annonce.json()
    assert annonce["statut"] == "disponible"
    assert len(annonce["photos"]) == 1

    catalogue = client.get(
        f"/api/v1/etablissements/{etablissement['id']}/marketplace/annonces", headers=acheteur_headers
    )
    assert catalogue.status_code == 200
    assert annonce["id"] in [a["id"] for a in catalogue.json()["items"]]

    # ---------------------------------------------------------------
    # 2. UC-20 : signalement par l'acheteur (curiosite), traite par l'A+ sans y donner suite
    # ---------------------------------------------------------------
    signalement = client.post(f"/api/v1/marketplace/annonces/{annonce['id']}/signaler", headers=acheteur_headers)
    assert signalement.status_code == 201
    en_attente = client.get(
        f"/api/v1/etablissements/{etablissement['id']}/marketplace/signalements", headers=admin_headers
    ).json()
    assert len(en_attente) == 1
    traitement = client.post(
        f"/api/v1/marketplace/signalements/{en_attente[0]['id']}/traiter",
        json={"decision": "Annonce conforme, aucune action necessaire."},
        headers=admin_headers,
    )
    assert traitement.status_code == 200

    # ---------------------------------------------------------------
    # 3. UC-21 : l'acheteur reserve puis paie (sequestre Kkiapay)
    # ---------------------------------------------------------------
    transaction = client.post(f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=acheteur_headers)
    assert transaction.status_code == 201
    transaction = transaction.json()
    assert transaction["statut"] == "en_attente_paiement"

    annonce_reservee = client.get(f"/api/v1/marketplace/annonces/{annonce['id']}", headers=vendeur_headers).json()
    assert annonce_reservee["statut"] == "reservee"

    amorcer = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-e2e4-{transaction['id']}"},
        headers=acheteur_headers,
    )
    assert amorcer.status_code == 200
    _payer_via_webhook(client, f"tx-e2e4-{transaction['id']}", secret)

    # ---------------------------------------------------------------
    # 4. UC-21 : remise en main propre declaree par le vendeur, confirmee par l'acheteur
    # ---------------------------------------------------------------
    remise = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/declarer-remise", headers=vendeur_headers
    )
    assert remise.status_code == 200
    assert remise.json()["statut"] == "remise_declaree"

    confirmation = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/confirmer", headers=acheteur_headers
    )
    assert confirmation.status_code == 200
    assert confirmation.json()["statut"] == "confirmee"

    # ---------------------------------------------------------------
    # 5. UC-21 : reversement manuel au vendeur par l'A+ de l'etablissement
    # ---------------------------------------------------------------
    reversement = client.post(
        f"/api/v1/marketplace/transactions/{transaction['id']}/reverser-vendeur",
        json={"reference_paiement": "MOMO-E2E4-REF-001"},
        headers=admin_headers,
    )
    assert reversement.status_code == 200
    assert reversement.json()["statut"] == "finalisee"

    annonce_finale = client.get(f"/api/v1/marketplace/annonces/{annonce['id']}", headers=acheteur_headers).json()
    assert annonce_finale["statut"] == "vendue"

    historique_vendeur = client.get("/api/v1/mes-annonces-marketplace", headers=vendeur_headers).json()
    assert len(historique_vendeur) == 1 and historique_vendeur[0]["statut"] == "vendue"
    historique_transactions_acheteur = client.get(
        "/api/v1/mes-transactions-marketplace", headers=acheteur_headers
    ).json()
    assert len(historique_transactions_acheteur) == 1 and historique_transactions_acheteur[0]["statut"] == "finalisee"
