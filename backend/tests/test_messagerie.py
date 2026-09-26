def test_groupe_classe_cree_automatiquement_et_accessible_a_ses_membres(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    conv_enseignant = client.get(
        f"/api/v1/classes/{ctx['classe']['id']}/conversation", headers=ctx["enseignant_headers"]
    )
    assert conv_enseignant.status_code == 200
    conv_eleve = client.get(f"/api/v1/classes/{ctx['classe']['id']}/conversation", headers=ctx["eleve_headers"])
    assert conv_eleve.status_code == 200
    conv_tuteur = client.get(f"/api/v1/classes/{ctx['classe']['id']}/conversation", headers=ctx["tuteur_headers"])
    assert conv_tuteur.status_code == 200
    assert conv_enseignant.json()["id"] == conv_eleve.json()["id"] == conv_tuteur.json()["id"]

    assert conv_eleve.json()["classe_niveau"] == ctx["classe"]["niveau"]

    conversation_id = conv_eleve.json()["id"]
    envoi = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"contenu": "Bonjour a tous"},
        headers=ctx["eleve_headers"],
    )
    assert envoi.status_code == 201
    assert envoi.json()["auteur_nom"] is not None

    messages_vus_par_enseignant = client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=ctx["enseignant_headers"]
    )
    assert messages_vus_par_enseignant.status_code == 200
    assert len(messages_vus_par_enseignant.json()) == 1
    assert messages_vus_par_enseignant.json()[0]["contenu"] == "Bonjour a tous"
    # Bug potentiel evite : sans le nom de l'auteur, un groupe de classe a plusieurs
    # participants serait illisible (impossible de savoir qui a ecrit quoi).
    assert messages_vus_par_enseignant.json()[0]["auteur_nom"] is not None

    aussi_dans_mes_conversations = client.get("/api/v1/conversations", headers=ctx["eleve_headers"])
    assert conversation_id in [c["id"] for c in aussi_dans_mes_conversations.json()]


def test_dm_adulte_eleve_interdit(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    depuis_enseignant = client.post(
        "/api/v1/conversations", json={"participant_id": eleve_id}, headers=ctx["enseignant_headers"]
    )
    assert depuis_enseignant.status_code == 403

    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]
    depuis_eleve = client.post(
        "/api/v1/conversations", json={"participant_id": enseignant_id}, headers=ctx["eleve_headers"]
    )
    assert depuis_eleve.status_code == 403


def test_dm_tuteur_eleve_autorise_seulement_pour_son_propre_enfant(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    ok = client.post("/api/v1/conversations", json={"participant_id": eleve_id}, headers=ctx["tuteur_headers"])
    assert ok.status_code == 201
    # Sans l'identite de "l'autre" participant, un DM serait impossible a afficher
    # utilement dans la liste des conversations.
    assert ok.json()["autre_participant_id"] == eleve_id
    assert ok.json()["autre_participant_nom"] is not None

    # Un meme DM redemande renvoie la conversation existante, pas un doublon.
    encore = client.post("/api/v1/conversations", json={"participant_id": eleve_id}, headers=ctx["tuteur_headers"])
    assert encore.status_code == 201
    assert encore.json()["id"] == ok.json()["id"]


def test_dm_tuteur_eleve_refuse_si_pas_son_enfant(client, classe_avec_enseignant_et_eleve, fake_email_client):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    autre_tuteur_payload = {
        "nom": "Adjovi", "prenom": "Kossi", "email": "kossi.adjovi.msg@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=autre_tuteur_payload)
    code = next(
        m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == autre_tuteur_payload["email"]
    )
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": autre_tuteur_payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": autre_tuteur_payload["email"], "mot_de_passe": autre_tuteur_payload["mot_de_passe"]},
    ).json()
    autre_tuteur_headers = {"Authorization": f"Bearer {login['access_token']}"}

    refus = client.post(
        "/api/v1/conversations", json={"participant_id": eleve_id}, headers=autre_tuteur_headers
    )
    assert refus.status_code == 403


def test_signalement_visible_et_traitable_par_admin(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    conversation_id = client.get(
        f"/api/v1/classes/{ctx['classe']['id']}/conversation", headers=ctx["eleve_headers"]
    ).json()["id"]
    message = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"contenu": "message problematique"},
        headers=ctx["eleve_headers"],
    ).json()

    signalement = client.post(f"/api/v1/messages/{message['id']}/signaler", headers=ctx["enseignant_headers"])
    assert signalement.status_code == 201
    assert signalement.json()["traite"] is False

    en_attente = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/signalements", headers=ctx["admin_headers"]
    )
    assert en_attente.status_code == 200
    assert len(en_attente.json()) == 1

    traitement = client.post(
        f"/api/v1/signalements/{signalement.json()['id']}/traiter",
        json={"decision": "Averti l'eleve, pas de suite"},
        headers=ctx["admin_headers"],
    )
    assert traitement.status_code == 200
    assert traitement.json()["traite"] is True

    plus_en_attente = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/signalements", headers=ctx["admin_headers"]
    )
    assert plus_en_attente.json() == []


def test_masquer_un_message_le_retire_seulement_pour_soi(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    conversation_id = client.get(
        f"/api/v1/classes/{ctx['classe']['id']}/conversation", headers=ctx["eleve_headers"]
    ).json()["id"]
    message = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"contenu": "a masquer"},
        headers=ctx["eleve_headers"],
    ).json()

    masquage = client.delete(f"/api/v1/messages/{message['id']}", headers=ctx["eleve_headers"])
    assert masquage.status_code == 204

    vue_eleve = client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=ctx["eleve_headers"])
    assert vue_eleve.json() == []
    vue_enseignant = client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=ctx["enseignant_headers"]
    )
    assert len(vue_enseignant.json()) == 1


def test_non_membre_ne_peut_pas_lire_ni_ecrire(client, classe_avec_enseignant_et_eleve, fake_email_client):
    ctx = classe_avec_enseignant_et_eleve
    conversation_id = client.get(
        f"/api/v1/classes/{ctx['classe']['id']}/conversation", headers=ctx["eleve_headers"]
    ).json()["id"]

    autre_enseignant_payload = {
        "nom": "Houngbo", "prenom": "Eric", "email": "eric.houngbo.msg@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/enseignants", json=autre_enseignant_payload)
    code = next(
        m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == autre_enseignant_payload["email"]
    )
    client.post("/api/v1/auth/enseignants/verify-otp", json={"email": autre_enseignant_payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login",
        json={
            "identifiant": autre_enseignant_payload["email"],
            "mot_de_passe": autre_enseignant_payload["mot_de_passe"],
        },
    ).json()
    autre_enseignant_headers = {"Authorization": f"Bearer {login['access_token']}"}

    refus_lecture = client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=autre_enseignant_headers
    )
    assert refus_lecture.status_code == 403
    refus_ecriture = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"contenu": "intrusion"},
        headers=autre_enseignant_headers,
    )
    assert refus_ecriture.status_code == 403
