import io


def _creer_cours(client, ctx, format="texte", contenu_texte="Le contenu du cours porte sur les fractions."):
    return client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Fractions", "chapitre": "Chapitre 1", "format": format, "contenu_texte": contenu_texte},
        headers=ctx["enseignant_headers"],
    ).json()


def test_ouvrir_session_est_idempotent_et_pose_une_question(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    cours = _creer_cours(client, ctx)

    session1 = client.post(f"/api/v1/cours/{cours['id']}/el-professor/session", headers=ctx["eleve_headers"]).json()
    session2 = client.post(f"/api/v1/cours/{cours['id']}/el-professor/session", headers=ctx["eleve_headers"]).json()
    assert session1["id"] == session2["id"]

    fake_llm_client.reponse_el_professor = "Une fraction represente une partie d'un tout."
    reponse = client.post(
        f"/api/v1/el-professor/sessions/{session1['id']}/messages",
        json={"question": "Qu'est-ce qu'une fraction ?"},
        headers=ctx["eleve_headers"],
    )
    assert reponse.status_code == 201
    messages = reponse.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "eleve"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["contenu"] == "Une fraction represente une partie d'un tout."

    consultation = client.get(f"/api/v1/cours/{cours['id']}/el-professor/session", headers=ctx["eleve_headers"])
    assert len(consultation.json()["messages"]) == 2


def test_session_appartient_a_un_seul_eleve(client, classe_avec_enseignant_et_eleve, fake_email_client):
    ctx = classe_avec_enseignant_et_eleve
    cours = _creer_cours(client, ctx)
    session = client.post(f"/api/v1/cours/{cours['id']}/el-professor/session", headers=ctx["eleve_headers"]).json()

    refus = client.post(
        f"/api/v1/el-professor/sessions/{session['id']}/messages",
        json={"question": "..."},
        headers=ctx["enseignant_headers"],
    )
    assert refus.status_code == 403


def test_echec_freellm_renvoie_une_erreur_explicite(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    cours = _creer_cours(client, ctx)
    session = client.post(f"/api/v1/cours/{cours['id']}/el-professor/session", headers=ctx["eleve_headers"]).json()

    fake_llm_client.echec_el_professor = True
    reponse = client.post(
        f"/api/v1/el-professor/sessions/{session['id']}/messages",
        json={"question": "Qu'est-ce qu'une fraction ?"},
        headers=ctx["eleve_headers"],
    )
    assert reponse.status_code == 502


def test_publication_cours_video_accepte_un_format_plus_grand(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    reponse = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Video de cours", "chapitre": "Chapitre 1", "format": "video"},
        files={"fichier": ("cours.mp4", io.BytesIO(b"contenu-video"), "video/mp4")},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.status_code == 201
    assert reponse.json()["format"] == "video"


def test_publication_cours_video_refuse_au_dela_de_200_mo(client, classe_avec_enseignant_et_eleve, monkeypatch):
    from app.modules.pedagogie import router as pedagogie_router

    monkeypatch.setattr(pedagogie_router, "MAX_TAILLE_COURS_VIDEO_OCTETS", 10)
    ctx = classe_avec_enseignant_et_eleve
    reponse = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Video trop lourde", "chapitre": "Chapitre 1", "format": "video"},
        files={"fichier": ("cours.mp4", io.BytesIO(b"contenu-video-plus-long-que-la-limite"), "video/mp4")},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.status_code == 413


# --- UC-27 : El Professor, volet enseignant ---


def _eleve_utilisateur_id(ctx, client):
    return client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]


def test_enseignant_ouvre_une_session_sur_un_eleve_de_sa_classe(
    client, fake_llm_client, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = _eleve_utilisateur_id(ctx, client)

    session = client.post(
        "/api/v1/el-professor-enseignant/sessions",
        json={"eleve_utilisateur_id": eleve_id, "sujet": "Difficultes de concentration"},
        headers=ctx["enseignant_headers"],
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    fake_llm_client.reponse_conseil_enseignant = "Essayez de fractionner les exercices en etapes courtes."
    reponse = client.post(
        f"/api/v1/el-professor-enseignant/sessions/{session_id}/messages",
        json={"question": "Cet eleve decroche vite en cours, que faire ?"},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.status_code == 201
    messages = reponse.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "enseignant"
    assert "fractionner" in messages[1]["contenu"]
    assert "⚠️" not in messages[1]["contenu"]


def test_session_refusee_pour_un_eleve_hors_de_ses_classes(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    refus = client.post(
        "/api/v1/el-professor-enseignant/sessions",
        json={"eleve_utilisateur_id": "id-eleve-inexistant"},
        headers=ctx["enseignant_headers"],
    )
    assert refus.status_code == 403


def test_question_generale_sans_eleve_precis_est_acceptee(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post(
        "/api/v1/el-professor-enseignant/sessions",
        json={"sujet": "Gestion de classe"},
        headers=ctx["enseignant_headers"],
    )
    assert session.status_code == 201
    assert session.json()["eleve_utilisateur_id"] is None


def test_signal_de_danger_declenche_une_alerte_et_une_recommandation_d_escalade(
    client, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = _eleve_utilisateur_id(ctx, client)
    session = client.post(
        "/api/v1/el-professor-enseignant/sessions",
        json={"eleve_utilisateur_id": eleve_id},
        headers=ctx["enseignant_headers"],
    ).json()

    reponse = client.post(
        f"/api/v1/el-professor-enseignant/sessions/{session['id']}/messages",
        json={"question": "Je crains une situation de maltraitance a la maison pour cet eleve, que faire ?"},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.status_code == 201
    assert "⚠️" in reponse.json()["messages"][1]["contenu"]

    alertes = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/alertes-el-professor", headers=ctx["admin_headers"]
    ).json()
    assert len(alertes) == 1
    assert alertes[0]["traite"] is False

    traitement = client.post(
        f"/api/v1/alertes-el-professor/{alertes[0]['id']}/traiter", headers=ctx["admin_headers"]
    )
    assert traitement.status_code == 200
    assert traitement.json()["traite"] is True


def test_enseignant_ne_voit_pas_les_alertes_ne_peut_pas_les_traiter(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    refus = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/alertes-el-professor", headers=ctx["enseignant_headers"]
    )
    assert refus.status_code == 403


def test_echec_freellm_conseiller_enseignant_renvoie_une_erreur_explicite(
    client, fake_llm_client, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post(
        "/api/v1/el-professor-enseignant/sessions", json={"sujet": "Test"}, headers=ctx["enseignant_headers"]
    ).json()

    fake_llm_client.echec_conseil_enseignant = True
    reponse = client.post(
        f"/api/v1/el-professor-enseignant/sessions/{session['id']}/messages",
        json={"question": "..."},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.status_code == 502


# --- UC-32 : El Professor, volet tuteur ---


def test_tuteur_ouvre_une_session_sur_son_enfant(client, fake_llm_client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    session = client.post(
        "/api/v1/el-professor-tuteur/sessions",
        json={"eleve_utilisateur_id": eleve_id, "sujet": "Motivation en baisse"},
        headers=ctx["tuteur_headers"],
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    fake_llm_client.reponse_conseil_tuteur = "Essayez de valoriser ses petites reussites au quotidien."
    reponse = client.post(
        f"/api/v1/el-professor-tuteur/sessions/{session_id}/messages",
        json={"question": "Mon enfant semble demotive, que faire ?"},
        headers=ctx["tuteur_headers"],
    )
    assert reponse.status_code == 201
    messages = reponse.json()["messages"]
    assert messages[0]["role"] == "tuteur"
    assert "valoriser" in messages[1]["contenu"]


def test_tuteur_ne_peut_pas_ouvrir_de_session_sur_un_eleve_qui_n_est_pas_son_enfant(
    client, classe_avec_enseignant_et_eleve, fake_email_client
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    autre_tuteur_payload = {
        "nom": "Zinsou", "prenom": "Paul", "email": "paul.zinsou.elprof@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=autre_tuteur_payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == autre_tuteur_payload["email"])
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": autre_tuteur_payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": autre_tuteur_payload["email"], "mot_de_passe": autre_tuteur_payload["mot_de_passe"]},
    ).json()
    autre_tuteur_headers = {"Authorization": f"Bearer {login['access_token']}"}

    refus = client.post(
        "/api/v1/el-professor-tuteur/sessions",
        json={"eleve_utilisateur_id": eleve_id},
        headers=autre_tuteur_headers,
    )
    assert refus.status_code == 403


def test_alerte_de_danger_visible_par_le_tuteur_et_par_l_administration(
    client, fake_llm_client, classe_avec_enseignant_et_eleve
):
    """UC-32.2 : une alerte declenchee depuis une session ENSEIGNANT doit etre visible
    par le tuteur de l'eleve concerne, en plus de l'administration - jamais l'inverse
    (un tuteur ne voit jamais les alertes des autres eleves)."""
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    session_enseignant = client.post(
        "/api/v1/el-professor-enseignant/sessions",
        json={"eleve_utilisateur_id": eleve_id},
        headers=ctx["enseignant_headers"],
    ).json()
    client.post(
        f"/api/v1/el-professor-enseignant/sessions/{session_enseignant['id']}/messages",
        json={"question": "Je crains une situation de maltraitance a la maison pour cet eleve, que faire ?"},
        headers=ctx["enseignant_headers"],
    )

    alertes_tuteur = client.get(
        f"/api/v1/mes-enfants/{eleve_id}/alertes-el-professor", headers=ctx["tuteur_headers"]
    )
    assert alertes_tuteur.status_code == 200
    assert len(alertes_tuteur.json()) == 1
    assert alertes_tuteur.json()[0]["origine"] == "enseignant"

    alertes_admin = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/alertes-el-professor", headers=ctx["admin_headers"]
    ).json()
    assert len(alertes_admin) == 1


def test_tuteur_ne_voit_pas_les_alertes_d_un_autre_eleve(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    refus = client.get(
        "/api/v1/mes-enfants/id-eleve-inexistant/alertes-el-professor", headers=ctx["tuteur_headers"]
    )
    assert refus.status_code == 403


def test_echec_freellm_conseiller_tuteur_renvoie_une_erreur_explicite(
    client, fake_llm_client, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    session = client.post(
        "/api/v1/el-professor-tuteur/sessions",
        json={"eleve_utilisateur_id": eleve_id},
        headers=ctx["tuteur_headers"],
    ).json()

    fake_llm_client.echec_conseil_tuteur = True
    reponse = client.post(
        f"/api/v1/el-professor-tuteur/sessions/{session['id']}/messages",
        json={"question": "..."},
        headers=ctx["tuteur_headers"],
    )
    assert reponse.status_code == 502


def test_session_famille_ne_peut_pas_recevoir_de_message_avant_que_l_enfant_ne_la_rejoigne(
    client, classe_avec_enseignant_et_eleve
):
    """UC-37.1 : co-initiation explicite (R3) - le tuteur cree/invite, mais aucun
    message n'est possible tant que l'enfant n'a pas explicitement rejoint le fil."""
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    session = client.post(
        "/api/v1/el-professor-famille/sessions",
        json={"eleve_utilisateur_id": eleve_id, "sujet": "Orientation en 3eme"},
        headers=ctx["tuteur_headers"],
    )
    assert session.status_code == 201
    session_id = session.json()["id"]
    assert session.json()["rejointe_le"] is None

    refus_tuteur = client.post(
        f"/api/v1/el-professor-famille/sessions/{session_id}/messages",
        json={"question": "Quelle filiere pour notre enfant ?"},
        headers=ctx["tuteur_headers"],
    )
    assert refus_tuteur.status_code == 409

    refus_eleve = client.post(
        f"/api/v1/el-professor-famille/sessions/{session_id}/messages",
        json={"question": "Je ne sais pas quoi choisir."},
        headers=ctx["eleve_headers"],
    )
    assert refus_eleve.status_code == 409

    rejoindre = client.post(
        f"/api/v1/el-professor-famille/sessions/{session_id}/rejoindre", headers=ctx["eleve_headers"]
    )
    assert rejoindre.status_code == 200
    assert rejoindre.json()["rejointe_le"] is not None


def test_tuteur_et_enfant_peuvent_tous_deux_ecrire_une_fois_la_session_rejointe(
    client, fake_llm_client, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    session_id = client.post(
        "/api/v1/el-professor-famille/sessions",
        json={"eleve_utilisateur_id": eleve_id},
        headers=ctx["tuteur_headers"],
    ).json()["id"]
    client.post(f"/api/v1/el-professor-famille/sessions/{session_id}/rejoindre", headers=ctx["eleve_headers"])

    reponse_tuteur = client.post(
        f"/api/v1/el-professor-famille/sessions/{session_id}/messages",
        json={"question": "Quelle filiere conseillez-vous ?"},
        headers=ctx["tuteur_headers"],
    )
    assert reponse_tuteur.status_code == 201
    assert reponse_tuteur.json()["messages"][0]["role"] == "tuteur"

    reponse_eleve = client.post(
        f"/api/v1/el-professor-famille/sessions/{session_id}/messages",
        json={"question": "Moi je pense plutot a un lycee technique."},
        headers=ctx["eleve_headers"],
    )
    assert reponse_eleve.status_code == 201
    roles = [m["role"] for m in reponse_eleve.json()["messages"]]
    assert roles == ["tuteur", "assistant", "eleve", "assistant"]


def test_alerte_famille_visible_par_l_administration_jamais_par_le_tuteur(
    client, fake_llm_client, classe_avec_enseignant_et_eleve
):
    """UC-37.2 : le tuteur peut etre la source du danger - une alerte declenchee dans un
    fil familial escalade directement vers l'administration, jamais vers le tuteur."""
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    session_id = client.post(
        "/api/v1/el-professor-famille/sessions",
        json={"eleve_utilisateur_id": eleve_id},
        headers=ctx["tuteur_headers"],
    ).json()["id"]
    client.post(f"/api/v1/el-professor-famille/sessions/{session_id}/rejoindre", headers=ctx["eleve_headers"])

    client.post(
        f"/api/v1/el-professor-famille/sessions/{session_id}/messages",
        json={"question": "Il y a de la violence a la maison, je ne sais plus quoi faire."},
        headers=ctx["eleve_headers"],
    )

    alertes_tuteur = client.get(
        f"/api/v1/mes-enfants/{eleve_id}/alertes-el-professor", headers=ctx["tuteur_headers"]
    ).json()
    assert alertes_tuteur == []

    alertes_admin = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/alertes-el-professor", headers=ctx["admin_headers"]
    ).json()
    assert len(alertes_admin) == 1
    assert alertes_admin[0]["origine"] == "famille"


def test_seul_le_couple_tuteur_enfant_concerne_accede_a_la_session_famille(
    client, classe_avec_enseignant_et_eleve, fake_email_client
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    session_id = client.post(
        "/api/v1/el-professor-famille/sessions",
        json={"eleve_utilisateur_id": eleve_id},
        headers=ctx["tuteur_headers"],
    ).json()["id"]

    autre_tuteur_payload = {
        "nom": "Alofa", "prenom": "Julie", "email": "julie.alofa.famille@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=autre_tuteur_payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == autre_tuteur_payload["email"])
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": autre_tuteur_payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": autre_tuteur_payload["email"], "mot_de_passe": autre_tuteur_payload["mot_de_passe"]},
    ).json()
    autre_tuteur_headers = {"Authorization": f"Bearer {login['access_token']}"}

    refus = client.get(f"/api/v1/el-professor-famille/sessions/{session_id}", headers=autre_tuteur_headers)
    assert refus.status_code == 404
