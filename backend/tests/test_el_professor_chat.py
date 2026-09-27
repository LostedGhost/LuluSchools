"""El Professor, interface de conversation complete : flux SSE, pieces jointes, aide
generale de l'eleve, renommage/suppression, alertes cote eleve, lecture a voix haute."""

import io
import json

import pymupdf as fitz

from app.core.llm import alleger_wav


def _evenements(reponse) -> list[tuple[str, dict]]:
    evenements = []
    for bloc in reponse.text.strip().split("\n\n"):
        lignes = dict(ligne.split(": ", 1) for ligne in bloc.splitlines())
        evenements.append((lignes["event"], json.loads(lignes["data"])))
    return evenements


def _poser(client, persona, session_id, headers, question="Explique-moi les fractions.", fichier=None):
    fichiers = {"fichier": fichier} if fichier else None
    return client.post(
        f"/api/v1/el-professor/{persona}/sessions/{session_id}/flux",
        data={"question": question},
        files=fichiers,
        headers=headers,
    )


def _pdf(texte: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 520, 770), texte)
    contenu = document.tobytes()
    document.close()
    return contenu


def _creer_cours(client, ctx, **donnees):
    data = {"titre": "Fractions", "chapitre": "Chapitre 1", "format": "texte", "contenu_texte": "Les fractions."}
    data.update(donnees.pop("data", {}))
    return client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours", data=data, headers=ctx["enseignant_headers"], **donnees
    ).json()


def test_conversation_generale_de_l_eleve_diffusee_puis_enregistree(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"])
    assert session.status_code == 201
    assert session.json()["cours_id"] is None

    reponse = _poser(client, "eleve", session.json()["id"], ctx["eleve_headers"])
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/event-stream")
    evenements = _evenements(reponse)
    assert [nom for nom, _ in evenements] == ["debut", "delta", "delta", "delta", "fin"]
    fin = evenements[-1][1]
    assert fin["message_assistant"]["contenu"] == "Voici une explication."
    assert fin["message_utilisateur"]["role"] == "eleve"

    # La consigne generale est adaptee au niveau de la classe de l'eleve.
    consigne = fake_llm_client.messages_flux_el_professor[-1][0]["content"]
    assert "CE1" in consigne and "devoir" in consigne

    liste = client.get("/api/v1/el-professor/eleve/sessions", headers=ctx["eleve_headers"]).json()
    assert len(liste) == 1 and len(liste[0]["messages"]) == 2


def test_plusieurs_conversations_generales_mais_une_seule_par_cours(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    cours = _creer_cours(client, ctx)
    a = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    b = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    assert a["id"] != b["id"]
    c1 = client.post("/api/v1/el-professor/eleve/sessions", json={"cours_id": cours["id"]}, headers=ctx["eleve_headers"]).json()
    c2 = client.post("/api/v1/el-professor/eleve/sessions", json={"cours_id": cours["id"]}, headers=ctx["eleve_headers"]).json()
    assert c1["id"] == c2["id"]
    assert c1["cours_titre"] == "Fractions"


def test_cours_pdf_transmis_a_el_professor_et_au_quiz(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    """Regression : un cours PDF n'a pas de contenu_texte - El Professor repondait sans
    rien savoir du cours et la generation de quiz etait impossible."""
    ctx = classe_avec_enseignant_et_eleve
    cours = _creer_cours(
        client,
        ctx,
        data={"format": "pdf", "contenu_texte": ""},
        files={"fichier": ("cours.pdf", io.BytesIO(_pdf("Le theoreme de Thales et les droites paralleles.")), "application/pdf")},
    )
    session = client.post("/api/v1/el-professor/eleve/sessions", json={"cours_id": cours["id"]}, headers=ctx["eleve_headers"]).json()
    _poser(client, "eleve", session["id"], ctx["eleve_headers"])
    assert "Thales" in fake_llm_client.messages_flux_el_professor[-1][0]["content"]

    quiz = client.post(f"/api/v1/cours/{cours['id']}/quiz", json={"nombre_questions": 2}, headers=ctx["enseignant_headers"])
    assert quiz.status_code == 201


def test_piece_jointe_image_envoyee_au_modele_vision_sans_etre_conservee(
    client, classe_avec_enseignant_et_eleve, fake_llm_client
):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    reponse = _poser(
        client, "eleve", session["id"], ctx["eleve_headers"], "Que vois-tu ?",
        ("exercice.png", io.BytesIO(b"\x89PNG-image"), "image/png"),
    )
    fin = _evenements(reponse)[-1][1]
    assert fin["message_utilisateur"]["piece_jointe_nom"] == "exercice.png"
    derniere_question = fake_llm_client.messages_flux_el_professor[-1][-1]["content"]
    assert derniere_question[1]["type"] == "image_url"
    assert derniere_question[1]["image_url"]["url"].startswith("data:image/png;base64,")

    # Au tour suivant, l'image n'est plus envoyee : seule sa mention reste.
    _poser(client, "eleve", session["id"], ctx["eleve_headers"], "Et ensuite ?")
    historique = fake_llm_client.messages_flux_el_professor[-1]
    assert "non conserve" in historique[1]["content"]
    assert isinstance(historique[-1]["content"], str)


def test_piece_jointe_pdf_lue_et_gardee_pour_la_suite(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post(
        "/api/v1/el-professor-enseignant/sessions", json={"sujet": "Sequence"}, headers=ctx["enseignant_headers"]
    ).json()
    texte = "Progression annuelle : fractions, proportionnalite, geometrie. " * 5
    _poser(
        client, "enseignant", session["id"], ctx["enseignant_headers"], "Ameliore ma progression.",
        ("progression.pdf", io.BytesIO(_pdf(texte)), "application/pdf"),
    )
    assert "proportionnalite" in fake_llm_client.messages_flux_el_professor[-1][-1]["content"]
    _poser(client, "enseignant", session["id"], ctx["enseignant_headers"], "Et pour le trimestre 2 ?")
    assert "proportionnalite" in fake_llm_client.messages_flux_el_professor[-1][1]["content"]


def test_piece_jointe_d_un_type_refuse(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    reponse = _poser(
        client, "eleve", session["id"], ctx["eleve_headers"], "Ecoute",
        ("question.mp3", io.BytesIO(b"ID3"), "audio/mpeg"),
    )
    assert reponse.status_code == 415


def test_echec_du_modele_n_enregistre_rien(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    fake_llm_client.echec_flux_el_professor = True
    evenements = _evenements(_poser(client, "eleve", session["id"], ctx["eleve_headers"]))
    assert evenements[-1][0] == "erreur"
    liste = client.get("/api/v1/el-professor/eleve/sessions", headers=ctx["eleve_headers"]).json()
    assert liste[0]["messages"] == []


def test_conversation_d_autrui_introuvable(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    assert _poser(client, "eleve", session["id"], ctx["enseignant_headers"]).status_code == 403
    session_prof = client.post(
        "/api/v1/el-professor-enseignant/sessions", json={}, headers=ctx["enseignant_headers"]
    ).json()
    # Un autre compte du meme role ne voit pas la conversation (404, pas 403).
    assert client.delete(
        f"/api/v1/el-professor/tuteur/sessions/{session_prof['id']}", headers=ctx["tuteur_headers"]
    ).status_code == 404
    assert _poser(client, "inconnue", session["id"], ctx["eleve_headers"]).status_code == 404


def test_detresse_d_un_eleve_alerte_l_administration_jamais_le_tuteur(
    client, classe_avec_enseignant_et_eleve, fake_llm_client
):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    evenements = _evenements(
        _poser(client, "eleve", session["id"], ctx["eleve_headers"], "Mon pere me frappe tous les soirs.")
    )
    assert "adulte de confiance" in evenements[-1][1]["message_assistant"]["contenu"]
    # Consigne renforcee avant l'appel : reponse courte, sans tableau, et jamais de numero.
    consigne = fake_llm_client.messages_flux_el_professor[-1][0]["content"]
    assert "sans tableau ni liste" in consigne and "numero de telephone" in consigne

    alertes = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/alertes-el-professor", headers=ctx["admin_headers"]
    ).json()
    assert [a["origine"] for a in alertes] == ["eleve"]
    eleve_id = session["eleve_utilisateur_id"]
    vues_tuteur = client.get(f"/api/v1/mes-enfants/{eleve_id}/alertes-el-professor", headers=ctx["tuteur_headers"]).json()
    assert vues_tuteur == []


def test_reponse_d_histoire_avec_un_mot_cle_n_alerte_pas_cote_eleve(
    client, classe_avec_enseignant_et_eleve, fake_llm_client
):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    fake_llm_client.morceaux_el_professor = ["La traite fut d'une violence extreme."]
    _poser(client, "eleve", session["id"], ctx["eleve_headers"], "Parle-moi de la traite negriere.")
    alertes = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/alertes-el-professor", headers=ctx["admin_headers"]
    ).json()
    assert alertes == []


def test_renommer_et_supprimer_une_conversation(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    _poser(client, "eleve", session["id"], ctx["eleve_headers"])

    renomme = client.patch(
        f"/api/v1/el-professor/eleve/sessions/{session['id']}", json={"sujet": "Revisions maths"}, headers=ctx["eleve_headers"]
    )
    assert renomme.json()["sujet"] == "Revisions maths"
    assert client.delete(f"/api/v1/el-professor/eleve/sessions/{session['id']}", headers=ctx["eleve_headers"]).status_code == 204
    assert client.get("/api/v1/el-professor/eleve/sessions", headers=ctx["eleve_headers"]).json() == []


def test_fil_familial_gere_par_le_tuteur_seulement(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    session = client.post(
        "/api/v1/el-professor-famille/sessions", json={"eleve_utilisateur_id": eleve_id}, headers=ctx["tuteur_headers"]
    ).json()
    # Pas de message avant que l'enfant n'ait rejoint le fil.
    assert _poser(client, "famille", session["id"], ctx["tuteur_headers"]).status_code == 409
    client.post(f"/api/v1/el-professor-famille/sessions/{session['id']}/rejoindre", headers=ctx["eleve_headers"])
    assert _poser(client, "famille", session["id"], ctx["eleve_headers"]).status_code == 200

    assert client.delete(
        f"/api/v1/el-professor/famille/sessions/{session['id']}", headers=ctx["eleve_headers"]
    ).status_code == 403
    assert client.delete(
        f"/api/v1/el-professor/famille/sessions/{session['id']}", headers=ctx["tuteur_headers"]
    ).status_code == 204


def test_lecture_a_voix_haute(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    reponse = client.post("/api/v1/el-professor/synthese-vocale", json={"texte": "Bonjour"}, headers=ctx["eleve_headers"])
    assert reponse.status_code == 200
    assert reponse.headers["content-type"] == "audio/wav"
    fake_llm_client.echec_synthese_vocale = True
    echec = client.post("/api/v1/el-professor/synthese-vocale", json={"texte": "Bonjour"}, headers=ctx["eleve_headers"])
    assert echec.status_code == 502


def test_messages_limites_par_jour(client, classe_avec_enseignant_et_eleve, limitation_debit, monkeypatch):
    from app.modules.pedagogie import el_professor_chat

    monkeypatch.setattr(el_professor_chat, "_MESSAGES_PAR_JOUR", 2)
    ctx = classe_avec_enseignant_et_eleve
    session = client.post("/api/v1/el-professor/eleve/sessions", json={}, headers=ctx["eleve_headers"]).json()
    assert _poser(client, "eleve", session["id"], ctx["eleve_headers"]).status_code == 200
    assert _poser(client, "eleve", session["id"], ctx["eleve_headers"]).status_code == 200
    refus = _poser(client, "eleve", session["id"], ctx["eleve_headers"])
    assert refus.status_code == 429
    assert "par jour" in refus.json()["error"]["message"]


def test_alleger_wav_divise_la_frequence_par_deux():
    import wave

    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x10\x00\x20\x00" * 1000)
    allege = alleger_wav(tampon.getvalue())
    with wave.open(io.BytesIO(allege)) as w:
        assert w.getframerate() == 12000
        assert w.getnframes() == 1000
    assert alleger_wav(b"pas du wav") == b"pas du wav"
