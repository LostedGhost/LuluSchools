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
