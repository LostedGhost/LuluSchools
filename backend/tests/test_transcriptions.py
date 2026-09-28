"""Lot 7.3 (handicap auditif) : transcription obligatoire des cours audio/video, sous-titres
WebVTT, mise en forme proposee par l'IA et relue par l'enseignant."""

import io

TRANSCRIPTION = "Bonjour a tous. Aujourd'hui nous etudions la photosynthese des plantes vertes."
VTT = "WEBVTT\n\n00:00.000 --> 00:04.000\nBonjour a tous.\n"


def _publier(client, ctx, format_cours="video", **data):
    fichiers = {"fichier": ("cours.mp4", io.BytesIO(b"contenu"), "video/mp4" if format_cours == "video" else "audio/mpeg")}
    if "sous_titres" in data:
        fichiers["sous_titres"] = ("cours.vtt", io.BytesIO(data.pop("sous_titres").encode()), "text/vtt")
    return client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Cours oral", "chapitre": "Chapitre 1", "format": format_cours, **data},
        files=fichiers,
        headers=ctx["enseignant_headers"],
    )


def test_cours_oral_refuse_sans_transcription(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    for format_cours in ("video", "audio"):
        reponse = _publier(client, ctx, format_cours)
        assert reponse.status_code == 422
        assert reponse.json()["error"]["code"] == "transcription_requise"
    trop_court = _publier(client, ctx, "audio", transcription="Bonjour")
    assert trop_court.status_code == 422


def test_cours_video_avec_transcription_et_sous_titres_lisibles_par_l_eleve(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    cours = _publier(client, ctx, transcription=TRANSCRIPTION, sous_titres=VTT)
    assert cours.status_code == 201
    assert cours.json()["transcription"] == TRANSCRIPTION
    assert cours.json()["a_des_sous_titres"] is True

    vue_eleve = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["eleve_headers"]).json()
    assert vue_eleve[0]["transcription"] == TRANSCRIPTION
    vtt = client.get(f"/api/v1/cours/{cours.json()['id']}/sous-titres", headers=ctx["eleve_headers"])
    assert vtt.status_code == 200
    assert vtt.headers["content-type"].startswith("text/vtt")
    assert vtt.text.startswith("WEBVTT")


def test_sous_titres_au_mauvais_format_refuses(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    reponse = _publier(client, ctx, transcription=TRANSCRIPTION, sous_titres="1\n00:00:00,000 --> 00:00:04,000\nSRT\n")
    assert reponse.status_code == 422
    assert reponse.json()["error"]["code"] == "sous_titres_invalides"


def test_transcription_corrigee_par_l_auteur_seulement(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    cours = _publier(client, ctx, transcription=TRANSCRIPTION).json()
    url = f"/api/v1/cours/{cours['id']}/transcription"
    nouvelle = {"transcription": TRANSCRIPTION + " Deuxieme partie.", "sous_titres_vtt": VTT}
    assert client.put(url, json=nouvelle, headers=ctx["eleve_headers"]).status_code == 403
    maj = client.put(url, json=nouvelle, headers=ctx["enseignant_headers"])
    assert maj.status_code == 200
    assert maj.json()["transcription"].endswith("Deuxieme partie.")
    assert maj.json()["a_des_sous_titres"] is True


def test_mise_en_forme_ia_est_une_proposition_non_enregistree(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    cours = _publier(client, ctx, transcription=TRANSCRIPTION).json()
    proposition = client.post(
        f"/api/v1/cours/{cours['id']}/transcription/mise-en-forme",
        json={"transcription": TRANSCRIPTION},
        headers=ctx["enseignant_headers"],
    )
    assert proposition.status_code == 200
    assert proposition.json()["transcription"].startswith("## Introduction")
    # Rien n'est ecrit tant que l'enseignant n'a pas enregistre (Art. 401 : l'humain decide).
    relu = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["enseignant_headers"]).json()
    assert relu[0]["transcription"] == TRANSCRIPTION

    fake_llm_client.echec_assistance = True
    echec = client.post(
        f"/api/v1/cours/{cours['id']}/transcription/mise-en-forme",
        json={"transcription": TRANSCRIPTION},
        headers=ctx["enseignant_headers"],
    )
    assert echec.status_code == 502


def test_quiz_genere_depuis_la_transcription_d_un_cours_audio(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    """Avant ce lot, un cours audio/video n'avait aucun texte : ni quiz ni El Professor."""
    ctx = classe_avec_enseignant_et_eleve
    cours = _publier(client, ctx, "audio", transcription=TRANSCRIPTION).json()
    quiz = client.post(f"/api/v1/cours/{cours['id']}/quiz", json={}, headers=ctx["enseignant_headers"])
    assert quiz.status_code == 201
