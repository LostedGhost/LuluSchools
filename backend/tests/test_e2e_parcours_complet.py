"""Test de bout en bout (etape 5 de la methode lucio-dev) : rejoue l'enchainement REEL
des cas d'utilisation de la Phase 1, dans l'ordre d'usage, avec les memes objets qui
circulent d'un module a l'autre. Contrairement aux tests unitaires par module (qui
valident chaque regle isolement), celui-ci verifie que les modules s'articulent
correctement - c'est ce niveau qui revele les problemes d'integration (etat partage,
ordre des operations, dependances entre ressources) qu'aucun test isole ne detecte.

Les regles metier deja couvertes par les tests unitaires (contestation, revision
manuelle, cas limites d'age/capacite, etc.) ne sont pas repetees ici : ce test suit
le chemin nominal complet, UC-01 a UC-10.
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


def test_parcours_complet_de_la_phase_1(client, fake_email_client, fake_files_client, fake_llm_client, admin_ministeriel_headers):
    # ---------------------------------------------------------------
    # 1. Le ministere cree l'etablissement -> premier compte A+ provisionne
    # ---------------------------------------------------------------
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Ecole Primaire de la Paix",
            "type": "EP",
            "statut": "public",
            "admin": {"nom": "Kone", "prenom": "Fatou", "email": "fatou.kone.e2e@example.com"},
        },
        headers=admin_ministeriel_headers,
    )
    assert etablissement.status_code == 201
    etablissement = etablissement.json()
    assert etablissement["code_etablissement"] == "EP01"

    mot_de_passe_admin_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "fatou.kone.e2e@example.com"
    )
    admin_headers, login_admin = _login(client, "fatou.kone.e2e@example.com", mot_de_passe_admin_temp)
    assert login_admin["doit_changer_mot_de_passe"] is True

    # Le mot de passe temporaire bloque reellement toute ecriture avant d'etre change.
    refus = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "CE1", "capacite": 5, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    )
    assert refus.status_code == 403
    assert refus.json()["error"]["code"] == "changement_mot_de_passe_requis"
    _changer_mot_de_passe(client, admin_headers, mot_de_passe_admin_temp)

    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "CE1", "capacite": 5, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    )
    assert classe.status_code == 201
    classe = classe.json()

    # ---------------------------------------------------------------
    # 2. Gouvernance des coefficients (UC-09) : referentiel national + proposition A+ validee par A++
    # ---------------------------------------------------------------
    coef_maths = client.post(
        "/api/v1/referentiels-coefficients",
        json={"niveau": "CE1", "matiere": "Mathematiques", "coefficient": 3},
        headers=admin_ministeriel_headers,
    )
    assert coef_maths.status_code == 201
    coef_sport = client.post(
        "/api/v1/referentiels-coefficients",
        json={"niveau": "CE1", "matiere": "Sport", "coefficient": 1},
        headers=admin_ministeriel_headers,
    )
    assert coef_sport.status_code == 201

    proposition = client.post(
        f"/api/v1/referentiels-coefficients/{coef_maths.json()['id']}/proposition",
        json={"coefficient": 4},
        headers=admin_headers,
    )
    assert proposition.status_code == 201
    validation = client.post(
        f"/api/v1/referentiels-coefficients/{proposition.json()['id']}/valider",
        headers=admin_ministeriel_headers,
    )
    assert validation.status_code == 200
    assert validation.json()["statut"] == "valide"
    # Le referentiel initial (coefficient 3) est desormais remplace par celui-ci (coefficient 4).

    # ---------------------------------------------------------------
    # 3. UC-01 : un tuteur cree son compte
    # ---------------------------------------------------------------
    tuteur_headers, _ = _signup_et_verifier(
        client, fake_email_client, "tuteurs", "Dossou", "Awa", "awa.dossou.e2e@example.com"
    )

    # ---------------------------------------------------------------
    # 4. UC-02/UC-03 : inscription d'un eleve majeur (16+), validation, matricule + compte auto-cree
    # ---------------------------------------------------------------
    date_naissance_17_ans = date(date.today().year - 17, date.today().month, 1).isoformat()
    inscription = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Dossou", "prenom": "Aisha", "date_naissance": date_naissance_17_ans, "classe_id": classe["id"]},
        headers=tuteur_headers,
    )
    assert inscription.status_code == 201
    inscription = inscription.json()
    assert inscription["statut"] == "soumise"

    validation_inscription = client.post(
        f"/api/v1/inscriptions/{inscription['id']}/valider", headers=admin_headers
    )
    assert validation_inscription.status_code == 200
    assert validation_inscription.json()["statut"] == "validee"

    identifiants_eleve = next(
        m for m in fake_email_client.sent if "login_id" in m and m.get("to_email") == "awa.dossou.e2e@example.com"
    )
    # Format matricule EP (proposition) : 7 (cycle EP) + 1 (national) + 00001 (sequence) + annee.
    assert len(identifiants_eleve["login_id"]) == 9
    assert identifiants_eleve["login_id"].startswith("71")

    eleve_headers, login_eleve = _login(client, identifiants_eleve["login_id"], identifiants_eleve["mot_de_passe"])
    assert login_eleve["doit_changer_mot_de_passe"] is True
    _changer_mot_de_passe(client, eleve_headers, identifiants_eleve["mot_de_passe"])

    # ---------------------------------------------------------------
    # 5. UC-04 : un enseignant cree son compte, postule a un poste, est note par l'IA
    # ---------------------------------------------------------------
    enseignant_headers, _ = _signup_et_verifier(
        client, fake_email_client, "enseignants", "Traore", "Moussa", "moussa.traore.e2e@example.com"
    )

    poste = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/postes",
        json={
            "titre": "Professeur des ecoles - CE1",
            "criteres": [
                {"type_document": "cv", "coefficient": 0.5, "seuil_minimal": 60},
                {"type_document": "diplome", "coefficient": 0.5, "seuil_minimal": 60},
            ],
        },
        headers=admin_headers,
    )
    assert poste.status_code == 201
    poste = poste.json()

    fake_llm_client.score_par_defaut = 85.0
    candidature = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv", "diplome"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"contenu cv"), "image/png")),
            ("fichiers", ("diplome.png", io.BytesIO(b"contenu diplome"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"contenu casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    )
    assert candidature.status_code == 201
    candidature = candidature.json()
    assert candidature["statut"] == "en_evaluation"
    assert candidature["score"] == 85.0
    # Seuls les 2 documents notes par l'IA passent par LuluFiles ; le casier judiciaire n'y transite jamais (Art. 395).
    assert len(fake_files_client.uploaded) == 2

    # ---------------------------------------------------------------
    # 6. UC-05 : contrat + signature par tracé manuel (canvas), puis reconduction (UC-05b)
    # ---------------------------------------------------------------
    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={
            "syllabus": "Programme de mathematiques et de sport, niveau CE1.",
            "date_fin": (date.today() + timedelta(days=20)).isoformat(),
        },
        headers=admin_headers,
    )
    assert contrat.status_code == 201
    contrat = contrat.json()

    signature = client.post(
        f"/api/v1/contrats/{contrat['id']}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace-du-canvas-en-png"), "image/png")},
        headers=enseignant_headers,
    )
    assert signature.status_code == 200
    assert signature.json()["statut"] == "signe"
    assert signature.json()["signature_image_lulufiles_id"] is not None

    reconduction = client.post(
        f"/api/v1/contrats/{contrat['id']}/reconduction",
        json={"syllabus": "Programme reconduit.", "date_fin": (date.today() + timedelta(days=385)).isoformat()},
        headers=admin_headers,
    )
    assert reconduction.status_code == 201
    nouveau_contrat_id = reconduction.json()["nouveau_contrat_id"]
    signature_reconduction = client.post(
        f"/api/v1/contrats/{nouveau_contrat_id}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace-du-canvas-en-png"), "image/png")},
        headers=enseignant_headers,
    )
    assert signature_reconduction.status_code == 200

    # ---------------------------------------------------------------
    # 7. UC-06/UC-07 : cours + quiz genere par l'IA
    # ---------------------------------------------------------------
    cours = client.post(
        f"/api/v1/classes/{classe['id']}/cours",
        data={
            "titre": "Les nombres jusqu'a 100",
            "chapitre": "Chapitre 1",
            "format": "texte",
            "contenu_texte": "Un nombre a deux chiffres a un chiffre des dizaines et un chiffre des unites.",
        },
        headers=enseignant_headers,
    )
    assert cours.status_code == 201
    cours = cours.json()

    quiz = client.post(
        f"/api/v1/cours/{cours['id']}/quiz",
        json={"seuil_reussite": 80, "nombre_questions": 2},
        headers=enseignant_headers,
    )
    assert quiz.status_code == 201
    quiz = quiz.json()
    assert len(quiz["questions"]) == 2
    assert "reponse_correcte_index" not in quiz["questions"][0]

    quiz_vu_par_eleve = client.get(f"/api/v1/quiz/{quiz['id']}", headers=eleve_headers)
    assert quiz_vu_par_eleve.status_code == 200

    premiere_tentative = client.post(
        f"/api/v1/quiz/{quiz['id']}/tentatives", json={"reponses": [1, 1]}, headers=eleve_headers
    )
    assert premiere_tentative.json()["reussie"] is False
    deuxieme_tentative = client.post(  # tentatives illimitees
        f"/api/v1/quiz/{quiz['id']}/tentatives", json={"reponses": [0, 0]}, headers=eleve_headers
    )
    assert deuxieme_tentative.json()["reussie"] is True

    # ---------------------------------------------------------------
    # 8. UC-08 : devoir (formulaire) en mathematiques, corrige automatiquement par l'IA
    # ---------------------------------------------------------------
    devoir_maths = client.post(
        f"/api/v1/classes/{classe['id']}/devoirs",
        json={
            "titre": "Addition et soustraction",
            "matiere": "Mathematiques",
            "date_limite": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "bareme": "flexible",
            "questions": [
                {"enonce": "Combien font 12 + 8 ?", "bareme_reponse": "La reponse attendue est 20.", "points_max": 10},
                {"enonce": "Combien font 15 - 5 ?", "bareme_reponse": "La reponse attendue est 10.", "points_max": 10},
            ],
        },
        headers=enseignant_headers,
    )
    assert devoir_maths.status_code == 201
    devoir_maths = devoir_maths.json()

    soumission = client.post(
        f"/api/v1/devoirs/{devoir_maths['id']}/soumissions",
        json={
            "reponses": [
                {"question_id": devoir_maths["questions"][0]["id"], "texte_reponse": "20"},
                {"question_id": devoir_maths["questions"][1]["id"], "texte_reponse": "10"},
            ]
        },
        headers=eleve_headers,
    )
    assert soumission.status_code == 201
    assert soumission.json()["statut"] == "corrigee"
    assert soumission.json()["note"] == 20.0  # 2 x 10 points, l'IA (fake) accorde tous les points

    # Devoir de sport, deja clos, sans soumission -> compte 0 dans la moyenne (absence = zero automatique).
    devoir_sport = client.post(
        f"/api/v1/classes/{classe['id']}/devoirs",
        json={
            "titre": "Echauffement",
            "matiere": "Sport",
            "date_limite": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "bareme": "flexible",
            "questions": [{"enonce": "Decris un echauffement.", "bareme_reponse": "N/A", "points_max": 10}],
        },
        headers=enseignant_headers,
    )
    assert devoir_sport.status_code == 201

    # ---------------------------------------------------------------
    # 9. UC-09 : bulletin pondere par les coefficients, puis validation de passage
    # ---------------------------------------------------------------
    # Mathematiques : 20/20 (100%), coefficient 4 (apres validation ministerielle).
    # Sport : 0/10 (0%, absence), coefficient 1.
    # Moyenne attendue : (100*4 + 0*1) / 5 = 80.
    eleve_id = client.get("/api/v1/me", headers=eleve_headers).json()["id"]
    bulletin = client.get(
        f"/api/v1/eleves/{eleve_id}/bulletins",
        params={"classe_id": classe["id"], "periode": "trimestre1"},
        headers=admin_headers,
    )
    assert bulletin.status_code == 200
    bulletin = bulletin.json()
    assert bulletin["moyenne_generale"] == 80.0

    passage = client.post(
        f"/api/v1/bulletins/{bulletin['id']}/valider-passage",
        json={"decision": "passage_classe_superieure"},
        headers=enseignant_headers,
    )
    assert passage.status_code == 200
    assert passage.json()["valide_par_conseil"] is True

    # ---------------------------------------------------------------
    # 10. UC-10 : actes academiques - reclamation gratuite, puis acte payant avec Kkiapay
    # ---------------------------------------------------------------
    reclamation = client.post(
        "/api/v1/demandes-actes",
        json={"est_reclamation": True, "reference_evaluation": devoir_maths["id"], "motif": "Verification du bareme"},
        headers=eleve_headers,
    )
    assert reclamation.status_code == 201
    assert reclamation.json()["statut"] == "en_traitement"

    type_acte = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/types-actes",
        json={
            "nom": "Attestation de succes",
            "prix": 1000,
            "pieces_requises": "Copie du CIP, acte de naissance",
            "condition_eligibilite": "Toutes les unites d'enseignement validees.",
        },
        headers=admin_headers,
    )
    assert type_acte.status_code == 201
    type_acte = type_acte.json()

    demande_payante = client.post(
        "/api/v1/demandes-actes", json={"type_acte_id": type_acte["id"]}, headers=tuteur_headers
    )
    # Un tuteur doit preciser l'eleve concerne.
    assert demande_payante.status_code == 422
    demande_payante = client.post(
        "/api/v1/demandes-actes",
        json={"type_acte_id": type_acte["id"], "eleve_utilisateur_id": eleve_id},
        headers=tuteur_headers,
    )
    assert demande_payante.status_code == 201
    demande_payante = demande_payante.json()
    assert demande_payante["statut"] == "soumise"

    amorce = client.post(
        f"/api/v1/demandes-actes/{demande_payante['id']}/paiement/amorcer",
        json={"transaction_id": "kkiapay-tx-e2e-1"},
        headers=tuteur_headers,
    )
    assert amorce.status_code == 200

    webhook = client.post(
        "/api/v1/paiements/webhook/kkiapay",
        json={"transactionId": "kkiapay-tx-e2e-1", "isPaymentSucces": True, "event": "transaction.success"},
        headers={"x-kkiapay-secret": _secret_de_test()},
    )
    assert webhook.status_code == 200

    demande_a_jour = client.get(f"/api/v1/demandes-actes/{demande_payante['id']}", headers=admin_headers)
    assert demande_a_jour.json()["statut"] == "en_traitement"

    traitement = client.post(
        f"/api/v1/demandes-actes/{demande_payante['id']}/traiter",
        json={"decision": "acceptee"},
        headers=admin_headers,
    )
    assert traitement.status_code == 200
    assert traitement.json()["statut"] == "acceptee"


def _secret_de_test() -> str:
    from app.core.config import settings

    return settings.kkiapay_secret
