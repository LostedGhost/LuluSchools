def _publier_cours_et_reussir_un_quiz(client, ctx):
    cours = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Les fractions", "chapitre": "Chapitre 3", "format": "texte", "contenu_texte": "1/2 + 1/2 = 1"},
        headers=ctx["enseignant_headers"],
    ).json()
    quiz = client.post(
        f"/api/v1/cours/{cours['id']}/quiz",
        json={"seuil_reussite": 80, "nombre_questions": 3},
        headers=ctx["enseignant_headers"],
    ).json()
    client.post(f"/api/v1/quiz/{quiz['id']}/tentatives", json={"reponses": [1, 1, 1]}, headers=ctx["eleve_headers"])
    client.post(f"/api/v1/quiz/{quiz['id']}/tentatives", json={"reponses": [0, 0, 0]}, headers=ctx["eleve_headers"])
    return cours, quiz


def test_eleve_voit_son_propre_passeport(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    cours, quiz = _publier_cours_et_reussir_un_quiz(client, ctx)

    passeport = client.get("/api/v1/eleves/me/passeport", headers=ctx["eleve_headers"])
    assert passeport.status_code == 200
    corps = passeport.json()
    assert corps["cours_suivis"] == [
        {"id": cours["id"], "titre": cours["titre"], "chapitre": cours["chapitre"], "format": "texte"}
    ]
    assert len(corps["quiz_reussis"]) == 1
    assert corps["quiz_reussis"][0]["quiz_id"] == quiz["id"]
    assert corps["quiz_reussis"][0]["score"] == 100.0
    assert {"id": "premier-quiz", "label": "Premier quiz reussi"} in corps["badges"]


def test_tuteur_voit_le_passeport_de_son_enfant(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_utilisateur_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    _publier_cours_et_reussir_un_quiz(client, ctx)

    passeport = client.get(f"/api/v1/mes-enfants/{eleve_utilisateur_id}/passeport", headers=ctx["tuteur_headers"])
    assert passeport.status_code == 200
    assert len(passeport.json()["quiz_reussis"]) == 1


def test_tuteur_ne_peut_pas_voir_le_passeport_d_un_eleve_qui_n_est_pas_son_enfant(
    client, classe_avec_enseignant_et_eleve, fake_email_client
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_utilisateur_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    autre_tuteur_payload = {
        "nom": "Adjahi", "prenom": "Nadia", "email": "nadia.adjahi.passeport@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=autre_tuteur_payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == autre_tuteur_payload["email"])
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": autre_tuteur_payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": autre_tuteur_payload["email"], "mot_de_passe": autre_tuteur_payload["mot_de_passe"]},
    ).json()
    autre_tuteur_headers = {"Authorization": f"Bearer {login['access_token']}"}

    refus = client.get(f"/api/v1/mes-enfants/{eleve_utilisateur_id}/passeport", headers=autre_tuteur_headers)
    assert refus.status_code == 403


def test_export_pdf_du_passeport(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    _publier_cours_et_reussir_un_quiz(client, ctx)

    export = client.post("/api/v1/eleves/me/passeport/export-pdf", headers=ctx["eleve_headers"])
    assert export.status_code == 200
    corps = export.json()
    assert corps["lulufiles_file_id"]
    assert corps["lien"].startswith("https://lulufiles-api.onrender.com/")
