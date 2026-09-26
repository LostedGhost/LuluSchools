from datetime import datetime, timedelta, timezone


def _planifier_session(client, ctx):
    date_heure = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    return client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/sessions-live",
        json={"date_heure": date_heure},
        headers=ctx["enseignant_headers"],
    ).json()


def test_eleve_sans_consentement_rejoint_en_lecture_seule(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)

    demarrage = client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    assert demarrage.status_code == 200
    assert demarrage.json()["statut"] == "en_cours"
    assert demarrage.json()["token_connexion"]

    participation = client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"])
    assert participation.status_code == 200
    assert participation.json()["camera_autorisee"] is False
    assert participation.json()["token_connexion"]


def test_eleve_avec_consentement_rejoint_avec_camera_autorisee(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    session = _planifier_session(client, ctx)
    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])

    consentement = client.post(
        f"/api/v1/eleves/{eleve_id}/consentement-camera-live", headers=ctx["tuteur_headers"]
    )
    assert consentement.status_code == 200

    participation = client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"])
    assert participation.json()["camera_autorisee"] is True


def test_consentement_refuse_pour_un_eleve_qui_n_est_pas_son_enfant(
    client, classe_avec_enseignant_et_eleve, fake_email_client
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    autre_tuteur_payload = {
        "nom": "Zinsou", "prenom": "Paul", "email": "paul.zinsou.live@example.com", "mot_de_passe": "Password1",
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
        f"/api/v1/eleves/{eleve_id}/consentement-camera-live", headers=autre_tuteur_headers
    )
    assert refus.status_code == 403


def test_seul_l_enseignant_organisateur_peut_demarrer_ou_terminer(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)

    refus = client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["eleve_headers"])
    assert refus.status_code == 403

    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    fin = client.post(f"/api/v1/sessions-live/{session['id']}/terminer", headers=ctx["enseignant_headers"])
    assert fin.status_code == 200
    assert fin.json()["statut"] == "terminee"

    refus_rejoindre = client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"])
    assert refus_rejoindre.status_code == 409


def test_eleve_peut_rejoindre_la_salle_sociale_avant_le_debut(client, classe_avec_enseignant_et_eleve):
    """UC-25.5 : la session n'a pas besoin d'etre demarree pour qu'un eleve la rejoigne
    (salle sociale pre-cours) - seul le tableau reste verrouille en ecriture."""
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)

    participation = client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"])
    assert participation.status_code == 200

    message = client.post(
        f"/api/v1/sessions-live/{session['id']}/messages",
        json={"contenu": "Bonjour, le prof n'est pas encore la !"},
        headers=ctx["eleve_headers"],
    )
    assert message.status_code == 201


# --- UC-25 : tableau collaboratif ---


def test_professeur_ecrit_sur_le_tableau_eleve_sans_permission_est_refuse(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)
    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"])

    etat = client.get(f"/api/v1/sessions-live/{session['id']}/tableau", headers=ctx["enseignant_headers"])
    assert etat.status_code == 200
    assert len(etat.json()["panneaux"]) == 1
    panneau_id = etat.json()["panneaux"][0]["panneau"]["id"]

    trait_prof = client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux/{panneau_id}/traits",
        json={"type": "trait_libre", "donnees": {"points": [[0.1, 0.1], [0.2, 0.2]], "epaisseur": 0.01}},
        headers=ctx["enseignant_headers"],
    )
    assert trait_prof.status_code == 201

    trait_eleve_refuse = client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux/{panneau_id}/traits",
        json={"type": "trait_libre", "donnees": {"points": [[0.3, 0.3], [0.4, 0.4]]}},
        headers=ctx["eleve_headers"],
    )
    assert trait_eleve_refuse.status_code == 403


def test_demande_de_craie_accordee_puis_revoquee(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    session = _planifier_session(client, ctx)
    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"])
    panneau_id = client.get(
        f"/api/v1/sessions-live/{session['id']}/tableau", headers=ctx["enseignant_headers"]
    ).json()["panneaux"][0]["panneau"]["id"]

    demande = client.post(f"/api/v1/sessions-live/{session['id']}/demande-craie", headers=ctx["eleve_headers"])
    assert demande.status_code == 201
    assert demande.json()["statut"] == "en_attente"

    demandes_prof = client.get(
        f"/api/v1/sessions-live/{session['id']}/demandes-craie", headers=ctx["enseignant_headers"]
    ).json()
    assert len(demandes_prof) == 1

    accord = client.post(
        f"/api/v1/sessions-live/{session['id']}/demandes-craie/{demande.json()['id']}/accorder",
        headers=ctx["enseignant_headers"],
    )
    assert accord.status_code == 200
    assert accord.json()["statut"] == "accordee"

    trait_eleve_ok = client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux/{panneau_id}/traits",
        json={"type": "trait_libre", "donnees": {"points": [[0.5, 0.5], [0.6, 0.6]]}},
        headers=ctx["eleve_headers"],
    )
    assert trait_eleve_ok.status_code == 201

    revocation = client.delete(
        f"/api/v1/sessions-live/{session['id']}/permissions-ecriture/{eleve_id}", headers=ctx["enseignant_headers"]
    )
    assert revocation.status_code == 204

    trait_eleve_refuse_apres_revocation = client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux/{panneau_id}/traits",
        json={"type": "trait_libre", "donnees": {"points": [[0.7, 0.7], [0.8, 0.8]]}},
        headers=ctx["eleve_headers"],
    )
    assert trait_eleve_refuse_apres_revocation.status_code == 403


def test_craie_pretee_directement_par_le_professeur(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    session = _planifier_session(client, ctx)
    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"])

    pret = client.post(
        f"/api/v1/sessions-live/{session['id']}/permissions-ecriture",
        json={"eleve_utilisateur_id": eleve_id},
        headers=ctx["enseignant_headers"],
    )
    assert pret.status_code == 201
    assert pret.json()["mode"] == "pretee"


def test_effacer_le_panneau_ajoute_un_trait_effacement(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)
    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    panneau_id = client.get(
        f"/api/v1/sessions-live/{session['id']}/tableau", headers=ctx["enseignant_headers"]
    ).json()["panneaux"][0]["panneau"]["id"]

    client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux/{panneau_id}/traits",
        json={"type": "trait_libre", "donnees": {"points": [[0.1, 0.1], [0.2, 0.2]]}},
        headers=ctx["enseignant_headers"],
    )
    effacement = client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux/{panneau_id}/effacer",
        headers=ctx["enseignant_headers"],
    )
    assert effacement.status_code == 201
    assert effacement.json()["type"] == "effacement"

    etat = client.get(f"/api/v1/sessions-live/{session['id']}/tableau", headers=ctx["enseignant_headers"]).json()
    assert len(etat["panneaux"][0]["traits"]) == 2


def test_nouveau_panneau_reserve_a_l_organisateur(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)
    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"])
    # Le panneau 0 est cree paresseusement au premier acces a l'etat du tableau.
    client.get(f"/api/v1/sessions-live/{session['id']}/tableau", headers=ctx["enseignant_headers"])

    refus = client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux", headers=ctx["eleve_headers"]
    )
    assert refus.status_code == 403

    reussite = client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux", headers=ctx["enseignant_headers"]
    )
    assert reussite.status_code == 201
    assert reussite.json()["ordre"] == 1


def test_capture_du_tableau_a_la_cloture_de_la_session(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)
    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    panneau_id = client.get(
        f"/api/v1/sessions-live/{session['id']}/tableau", headers=ctx["enseignant_headers"]
    ).json()["panneaux"][0]["panneau"]["id"]
    client.post(
        f"/api/v1/sessions-live/{session['id']}/tableau/panneaux/{panneau_id}/traits",
        json={"type": "texte", "donnees": {"x": 0.1, "y": 0.1, "texte": "Titre du cours"}},
        headers=ctx["enseignant_headers"],
    )

    client.post(f"/api/v1/sessions-live/{session['id']}/terminer", headers=ctx["enseignant_headers"])

    captures = client.get(
        f"/api/v1/sessions-live/{session['id']}/captures", headers=ctx["enseignant_headers"]
    ).json()
    assert len(captures) == 1
    assert captures[0]["panneau_id"] == panneau_id


def test_canal_temps_reel_diffuse_un_trait_ajoute_par_rest(client, classe_avec_enseignant_et_eleve):
    """Verifie que le canal WebSocket diffuse bien un evenement declenche par un appel
    REST classique (pas de logique metier dans le canal lui-meme, voir realtime.py)."""
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)
    client.post(f"/api/v1/sessions-live/{session['id']}/demarrer", headers=ctx["enseignant_headers"])
    panneau_id = client.get(
        f"/api/v1/sessions-live/{session['id']}/tableau", headers=ctx["enseignant_headers"]
    ).json()["panneaux"][0]["panneau"]["id"]

    jeton_prof = ctx["enseignant_headers"]["Authorization"].split(" ")[1]
    with client.websocket_connect(f"/api/v1/ws/sessions-live/{session['id']}?token={jeton_prof}") as websocket:
        client.post(
            f"/api/v1/sessions-live/{session['id']}/tableau/panneaux/{panneau_id}/traits",
            json={"type": "trait_libre", "donnees": {"points": [[0.1, 0.1], [0.9, 0.9]]}},
            headers=ctx["enseignant_headers"],
        )
        evenement = websocket.receive_json()
        assert evenement["type"] == "trait"
        assert evenement["panneau_id"] == panneau_id


def test_canal_temps_reel_refuse_un_jeton_invalide(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = _planifier_session(client, ctx)

    from starlette.websockets import WebSocketDisconnect
    import pytest

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/sessions-live/{session['id']}?token=jeton-invalide"):
            pass
