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
