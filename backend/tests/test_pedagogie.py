def test_publier_cours_texte_et_le_lister(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    response = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Les fractions", "chapitre": "Chapitre 3", "format": "texte", "contenu_texte": "1/2 + 1/2 = 1"},
        headers=ctx["enseignant_headers"],
    )
    assert response.status_code == 201

    liste = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["eleve_headers"])
    assert liste.status_code == 200
    assert len(liste.json()) == 1


def test_eleve_non_inscrit_ne_peut_pas_lister_les_cours(
    client, fake_email_client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Les fractions", "chapitre": "Chapitre 3", "format": "texte"},
        headers=ctx["enseignant_headers"],
    )

    # Un tuteur/eleve d'un tout autre etablissement (donc non inscrit dans cette classe).
    autre_etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Autre ecole",
            "type": "EP",
            "statut": "public",
            "admin": {"nom": "Zinsou", "prenom": "Paul", "email": "paul.zinsou@example.com"},
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "paul.zinsou@example.com"
    )
    login_autre_admin = client.post(
        "/api/v1/auth/login", json={"identifiant": "paul.zinsou@example.com", "mot_de_passe": mot_de_passe_temp}
    ).json()
    autre_admin_headers = {"Authorization": f"Bearer {login_autre_admin['access_token']}"}
    autre_classe = client.post(
        f"/api/v1/etablissements/{autre_etablissement['id']}/classes",
        json={"niveau": "CE1", "capacite": 30, "politique_depassement": "ordre_arrivee"},
        headers=autre_admin_headers,
    ).json()

    client.post(
        "/api/v1/auth/tuteurs",
        json={"nom": "Autre", "prenom": "Tuteur", "email": "autre.tuteur@example.com", "mot_de_passe": "Password1"},
    )
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == "autre.tuteur@example.com")
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": "autre.tuteur@example.com", "code": code})
    login_autre_tuteur = client.post(
        "/api/v1/auth/login", json={"identifiant": "autre.tuteur@example.com", "mot_de_passe": "Password1"}
    ).json()
    autre_tuteur_headers = {"Authorization": f"Bearer {login_autre_tuteur['access_token']}"}

    inscription = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Autre", "prenom": "Eleve", "date_naissance": "2005-01-01", "classe_id": autre_classe["id"]},
        headers=autre_tuteur_headers,
    ).json()
    client.post(f"/api/v1/inscriptions/{inscription['id']}/valider", headers=autre_admin_headers)
    identifiants = next(m for m in fake_email_client.sent if "login_id" in m and m.get("to_email") == "autre.tuteur@example.com")
    login_autre_eleve = client.post(
        "/api/v1/auth/login",
        json={"identifiant": identifiants["login_id"], "mot_de_passe": identifiants["mot_de_passe"]},
    ).json()
    autre_eleve_headers = {"Authorization": f"Bearer {login_autre_eleve['access_token']}"}

    response = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=autre_eleve_headers)
    assert response.status_code == 403


def test_quiz_genere_par_le_llm_et_tentative_illimitee(client, fake_llm_client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    cours = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={
            "titre": "Les fractions",
            "chapitre": "Chapitre 3",
            "format": "texte",
            "contenu_texte": "1/2 + 1/2 = 1",
        },
        headers=ctx["enseignant_headers"],
    ).json()

    quiz = client.post(
        f"/api/v1/cours/{cours['id']}/quiz",
        json={"seuil_reussite": 80, "nombre_questions": 3},
        headers=ctx["enseignant_headers"],
    ).json()
    assert len(quiz["questions"]) == 3
    assert "reponse_correcte_index" not in quiz["questions"][0]

    echec = client.post(
        f"/api/v1/quiz/{quiz['id']}/tentatives", json={"reponses": [1, 1, 1]}, headers=ctx["eleve_headers"]
    )
    assert echec.status_code == 201
    assert echec.json()["score"] == 0.0
    assert echec.json()["reussie"] is False

    reussite = client.post(
        f"/api/v1/quiz/{quiz['id']}/tentatives", json={"reponses": [0, 0, 0]}, headers=ctx["eleve_headers"]
    )
    assert reussite.status_code == 201
    assert reussite.json()["score"] == 100.0
    assert reussite.json()["reussie"] is True


def test_generation_quiz_sans_contenu_texte_est_refusee(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    cours = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Sans contenu", "chapitre": "Chapitre 1", "format": "pdf"},
        headers=ctx["enseignant_headers"],
    ).json()
    response = client.post(f"/api/v1/cours/{cours['id']}/quiz", json={}, headers=ctx["enseignant_headers"])
    assert response.status_code == 422


def test_generation_quiz_echouee_renvoie_502(client, fake_llm_client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    fake_llm_client.echec_generation_quiz = True
    cours = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Les fractions", "chapitre": "Chapitre 3", "format": "texte", "contenu_texte": "contenu"},
        headers=ctx["enseignant_headers"],
    ).json()
    response = client.post(f"/api/v1/cours/{cours['id']}/quiz", json={}, headers=ctx["enseignant_headers"])
    assert response.status_code == 502
