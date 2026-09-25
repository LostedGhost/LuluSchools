"""Test de bout en bout (etape 5 de la methode lucio-dev) pour les Phases 2 et 3 :
rejoue l'enchainement REEL des UC-11 a UC-19, dans un ordre d'usage plausible, avec
les memes objets (etablissement, classe, enseignant, eleve, tuteur) qui circulent
d'un module a l'autre - exactement comme test_e2e_parcours_complet.py pour la Phase 1.

Les regles metier deja couvertes par les tests unitaires par module (remboursements,
delais, cas de refus RBAC, validation tacite, etc.) ne sont pas repetees ici : ce test
suit le chemin nominal complet, UC-11 a UC-19.
"""

import io
from datetime import date, datetime, timedelta, timezone


def _signup_et_verifier(client, fake_email_client, chemin, nom, prenom, email, mot_de_passe="Password1"):
    client.post(f"/api/v1/auth/{chemin}", json={"nom": nom, "prenom": prenom, "email": email, "mot_de_passe": mot_de_passe})
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == email)
    verif = client.post(f"/api/v1/auth/{chemin}/verify-otp", json={"email": email, "code": code})
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


def _payer_via_webhook(client, transaction_id, secret):
    reponse = client.post(
        "/api/v1/paiements/webhook/kkiapay",
        json={"transactionId": transaction_id, "isPaymentSucces": True, "event": "transaction.success"},
        headers={"x-kkiapay-secret": secret},
    )
    assert reponse.status_code == 200


def test_parcours_complet_des_phases_2_et_3(
    client, fake_email_client, fake_llm_client, admin_ministeriel_headers, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "kkiapay_secret", "secret-de-test-e2e")
    secret = "secret-de-test-e2e"

    # ---------------------------------------------------------------
    # 0. Socle Phase 1 : etablissement, classe, tuteur+eleve inscrit, enseignant sous contrat signe
    #    (necessaire : messagerie/transport/cantine/live/micro-jobs dependent tous d'un
    #    enseignant reellement rattache et d'un eleve reellement inscrit).
    # ---------------------------------------------------------------
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "College Saint-Michel",
            "type": "ES",
            "statut": "prive",
            "admin": {"nom": "Agbo", "prenom": "Julienne", "email": "julienne.agbo.e2e23@example.com"},
        },
        headers=admin_ministeriel_headers,
    )
    assert etablissement.status_code == 201
    etablissement = etablissement.json()

    mot_de_passe_admin_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "julienne.agbo.e2e23@example.com"
    )
    admin_headers, _ = _login(client, "julienne.agbo.e2e23@example.com", mot_de_passe_admin_temp)
    _changer_mot_de_passe(client, admin_headers, mot_de_passe_admin_temp)

    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "6eme", "capacite": 5, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    ).json()

    tuteur_headers, _ = _signup_et_verifier(
        client, fake_email_client, "tuteurs", "Houessou", "Clarisse", "clarisse.houessou.e2e23@example.com"
    )
    date_naissance_12_ans = date(date.today().year - 12, date.today().month, 1).isoformat()
    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Houessou", "prenom": "Marcel", "date_naissance": date_naissance_12_ans,
            "classe_id": classe["id"], "consentement_parental_donne": True,
        },
        headers=tuteur_headers,
    )
    assert inscription.status_code == 201
    client.post(f"/api/v1/inscriptions/{inscription.json()['id']}/valider", headers=admin_headers)
    identifiants_eleve = next(
        m for m in fake_email_client.sent if "login_id" in m and m.get("to_email") == "clarisse.houessou.e2e23@example.com"
    )
    eleve_headers, _ = _login(client, identifiants_eleve["login_id"], identifiants_eleve["mot_de_passe"])
    _changer_mot_de_passe(client, eleve_headers, identifiants_eleve["mot_de_passe"])
    eleve_id = client.get("/api/v1/me", headers=eleve_headers).json()["id"]

    enseignant_headers, _ = _signup_et_verifier(
        client, fake_email_client, "enseignants", "Zannou", "Firmin", "firmin.zannou.e2e23@example.com"
    )
    poste = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/postes",
        json={"titre": "Professeur d'histoire", "criteres": [{"type_document": "cv", "coefficient": 1, "seuil_minimal": 0}]},
        headers=admin_headers,
    ).json()
    fake_llm_client.score_par_defaut = 90.0
    candidature = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"cv"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    ).json()
    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Histoire du Benin", "date_fin": (date.today() + timedelta(days=300)).isoformat()},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/contrats/{contrat['id']}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace-canvas"), "image/png")},
        headers=enseignant_headers,
    )
    enseignant_id = client.get("/api/v1/me", headers=enseignant_headers).json()["id"]

    # ---------------------------------------------------------------
    # 1. UC-13 : messagerie - groupe de classe auto-cree, DM tuteur -> son enfant,
    #    signalement traite par l'A+
    # ---------------------------------------------------------------
    groupe_classe = client.get(f"/api/v1/classes/{classe['id']}/conversation", headers=enseignant_headers)
    assert groupe_classe.status_code == 200
    conversation_id = groupe_classe.json()["id"]
    assert client.get(f"/api/v1/classes/{classe['id']}/conversation", headers=eleve_headers).json()["id"] == conversation_id
    assert client.get(f"/api/v1/classes/{classe['id']}/conversation", headers=tuteur_headers).json()["id"] == conversation_id

    message = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"contenu": "Rappel : sortie pedagogique vendredi."},
        headers=enseignant_headers,
    )
    assert message.status_code == 201

    dm_refuse = client.post("/api/v1/conversations", json={"participant_id": eleve_id}, headers=enseignant_headers)
    assert dm_refuse.status_code == 403  # DM adulte->eleve interdit, seul le groupe de classe est autorise

    dm_tuteur_eleve = client.post("/api/v1/conversations", json={"participant_id": eleve_id}, headers=tuteur_headers)
    assert dm_tuteur_eleve.status_code == 201

    signalement = client.post(f"/api/v1/messages/{message.json()['id']}/signaler", headers=eleve_headers)
    assert signalement.status_code == 201
    en_attente = client.get(f"/api/v1/etablissements/{etablissement['id']}/signalements", headers=admin_headers)
    assert len(en_attente.json()) == 1
    traitement = client.post(
        f"/api/v1/signalements/{signalement.json()['id']}/traiter",
        json={"decision": "Message verifie, sans suite."},
        headers=admin_headers,
    )
    assert traitement.status_code == 200

    # ---------------------------------------------------------------
    # 2. UC-14/UC-15 : cours texte + assistant El Professor, cours video
    # ---------------------------------------------------------------
    cours = client.post(
        f"/api/v1/classes/{classe['id']}/cours",
        data={
            "titre": "L'independance du Benin", "chapitre": "Chapitre 3", "format": "texte",
            "contenu_texte": "Le Benin a obtenu son independance le 1er aout 1960.",
        },
        headers=enseignant_headers,
    ).json()

    fake_llm_client.reponse_el_professor = "Le Benin est devenu independant le 1er aout 1960."
    session_el_prof = client.post(f"/api/v1/cours/{cours['id']}/el-professor/session", headers=eleve_headers)
    assert session_el_prof.status_code == 201
    reponse_el_prof = client.post(
        f"/api/v1/el-professor/sessions/{session_el_prof.json()['id']}/messages",
        json={"question": "Quelle est la date de l'independance ?"},
        headers=eleve_headers,
    )
    assert reponse_el_prof.status_code == 201
    assert reponse_el_prof.json()["messages"][-1]["contenu"] == fake_llm_client.reponse_el_professor

    cours_video = client.post(
        f"/api/v1/classes/{classe['id']}/cours",
        data={"titre": "Documentaire", "chapitre": "Chapitre 3", "format": "video"},
        files={"fichier": ("doc.mp4", io.BytesIO(b"contenu-video"), "video/mp4")},
        headers=enseignant_headers,
    )
    assert cours_video.status_code == 201

    # ---------------------------------------------------------------
    # 3. UC-16 : cours en direct - consentement camera, demarrage, participation, fin
    # ---------------------------------------------------------------
    session_live = client.post(
        f"/api/v1/classes/{classe['id']}/sessions-live",
        json={"date_heure": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        headers=enseignant_headers,
    ).json()
    client.post(f"/api/v1/eleves/{eleve_id}/consentement-camera-live", headers=tuteur_headers)
    demarrage = client.post(f"/api/v1/sessions-live/{session_live['id']}/demarrer", headers=enseignant_headers)
    assert demarrage.status_code == 200
    participation = client.post(f"/api/v1/sessions-live/{session_live['id']}/rejoindre", headers=eleve_headers)
    assert participation.status_code == 200
    assert participation.json()["camera_autorisee"] is True
    fin_live = client.post(f"/api/v1/sessions-live/{session_live['id']}/terminer", headers=enseignant_headers)
    assert fin_live.status_code == 200

    # ---------------------------------------------------------------
    # 4. UC-11/UC-12 : ticket de transport et de cantine, l'enseignant cumule les deux
    #    designations de Controleur/Ticketeur
    # ---------------------------------------------------------------
    client.post(
        f"/api/v1/etablissements/{etablissement['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "transport"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/etablissements/{etablissement['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "cantine"},
        headers=admin_headers,
    )

    ligne = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/lignes-transport",
        json={"nom": "Ligne Cotonou-Centre", "prix": 300, "capacite_par_trajet": 20},
        headers=admin_headers,
    ).json()
    demain = (date.today() + timedelta(days=5)).isoformat()
    ticket_transport = client.post(
        f"/api/v1/lignes-transport/{ligne['id']}/tickets", json={"date_trajet": demain}, headers=eleve_headers
    ).json()
    client.post(
        f"/api/v1/tickets-transport/{ticket_transport['id']}/paiement/amorcer",
        json={"transaction_id": "tx-e2e-transport"},
        headers=eleve_headers,
    )
    _payer_via_webhook(client, "tx-e2e-transport", secret)
    validation_transport = client.post(
        f"/api/v1/tickets-transport/{ticket_transport['id']}/valider", headers=enseignant_headers
    )
    assert validation_transport.status_code == 200
    assert validation_transport.json()["statut"] == "valide"

    type_repas = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/types-repas-cantine",
        json={"nom": "Menu unique", "prix": 500, "capacite_par_jour": 50},
        headers=admin_headers,
    ).json()
    ticket_cantine = client.post(
        f"/api/v1/types-repas-cantine/{type_repas['id']}/tickets", json={"date_service": demain}, headers=eleve_headers
    ).json()
    client.post(
        f"/api/v1/tickets-cantine/{ticket_cantine['id']}/paiement/amorcer",
        json={"transaction_id": "tx-e2e-cantine"},
        headers=eleve_headers,
    )
    _payer_via_webhook(client, "tx-e2e-cantine", secret)
    validation_cantine = client.post(
        f"/api/v1/tickets-cantine/{ticket_cantine['id']}/valider", headers=enseignant_headers
    )
    assert validation_cantine.status_code == 200
    assert validation_cantine.json()["statut"] == "valide"

    # ---------------------------------------------------------------
    # 5. UC-17 : billetterie - evenement payant, meme controleur designe pour cet evenement
    # ---------------------------------------------------------------
    evenement = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/evenements",
        json={
            "titre": "Kermesse de fin d'annee", "description": "Fete de l'ecole", "lieu": "Cour principale",
            "date_heure": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "capacite_max": 100, "prix_billet": 1000,
        },
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/etablissements/{etablissement['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "evenement", "evenement_id": evenement["id"]},
        headers=admin_headers,
    )
    billet = client.post(f"/api/v1/evenements/{evenement['id']}/billets", headers=tuteur_headers).json()
    client.post(
        f"/api/v1/billets/{billet['id']}/paiement/amorcer", json={"transaction_id": "tx-e2e-billet"}, headers=tuteur_headers
    )
    _payer_via_webhook(client, "tx-e2e-billet", secret)
    validation_billet = client.post(f"/api/v1/billets/{billet['id']}/valider", headers=enseignant_headers)
    assert validation_billet.status_code == 200
    assert validation_billet.json()["statut"] == "valide"

    # ---------------------------------------------------------------
    # 6. UC-19 : visite virtuelle 3D publiee par l'A+
    # ---------------------------------------------------------------
    visite = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/visites-virtuelles",
        json={"type": "3d", "lien_externe": "https://matterport.example.com/college-saint-michel", "attestation_autorisation": True},
        headers=admin_headers,
    )
    assert visite.status_code == 201

    # ---------------------------------------------------------------
    # 7. UC-18 : micro-job - l'enseignant propose, le tuteur accepte, sequestre puis reversement
    # ---------------------------------------------------------------
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours de soutien en histoire", "description": "2h de soutien pour un eleve de 6eme", "prix": 8000},
        headers=enseignant_headers,
    ).json()
    mission = client.post(f"/api/v1/micro-jobs/offres/{offre['id']}/accepter", headers=tuteur_headers).json()
    client.post(
        f"/api/v1/missions-micro-job/{mission['id']}/paiement/amorcer",
        json={"transaction_id": "tx-e2e-microjob"},
        headers=tuteur_headers,
    )
    _payer_via_webhook(client, "tx-e2e-microjob", secret)
    fin_mission = client.post(f"/api/v1/missions-micro-job/{mission['id']}/declarer-fin", headers=enseignant_headers)
    assert fin_mission.status_code == 200
    assert fin_mission.json()["statut"] == "terminee_declaree"
    validation_mission = client.post(f"/api/v1/missions-micro-job/{mission['id']}/valider", headers=tuteur_headers)
    assert validation_mission.status_code == 200
    assert validation_mission.json()["statut"] == "validee"
    reversement = client.post(
        f"/api/v1/missions-micro-job/{mission['id']}/reverser-prestataire",
        json={"reference_paiement": "MOMO-E2E-REF"},
        headers=admin_ministeriel_headers,
    )
    assert reversement.status_code == 200
    assert reversement.json()["statut"] == "payee"

    # ---------------------------------------------------------------
    # Verification finale : chaque module retrouve bien son propre historique pour ces
    # memes utilisateurs (integration correcte, pas de fuite entre modules).
    # ---------------------------------------------------------------
    assert len(client.get("/api/v1/mes-tickets-transport", headers=eleve_headers).json()) == 1
    assert len(client.get("/api/v1/mes-tickets-cantine", headers=eleve_headers).json()) == 1
    assert len(client.get("/api/v1/mes-billets", headers=tuteur_headers).json()) == 1
    assert len(client.get("/api/v1/mes-missions-micro-job", headers=enseignant_headers).json()) == 1
    assert len(client.get("/api/v1/mes-missions-micro-job", headers=tuteur_headers).json()) == 1
