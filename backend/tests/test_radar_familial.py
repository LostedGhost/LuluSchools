from datetime import date, timedelta

import pytest


def test_radar_sans_activite_ne_fait_aucun_appel_llm(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    """UC-36.1/36.2 : sans le moindre fait, aucune affirmation IA non tracable n'est
    generee - on evite meme l'appel LLM."""
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    fake_llm_client.echec_digest_famille = True  # prouve qu'on ne l'appelle pas
    radar = client.get(f"/api/v1/mes-enfants/{eleve_id}/radar-familial", headers=ctx["tuteur_headers"])
    assert radar.status_code == 200
    assert radar.json()["sources"] == []
    assert "notable" in radar.json()["resume"]


def _eleve_id_de_la_classe(client, ctx):
    eleves = client.get(f"/api/v1/classes/{ctx['classe']['id']}/eleves", headers=ctx["enseignant_headers"]).json()
    return eleves[0]["eleve_id"]


def test_radar_cite_les_entrees_de_vie_scolaire_de_la_semaine(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_utilisateur_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    eleve_id = _eleve_id_de_la_classe(client, ctx)

    aujourd_hui = date.today().isoformat()
    entree = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/eleves/{eleve_id}/vie-scolaire",
        json={
            "nature": "felicitation",
            "matiere": "Mathematiques",
            "description": "Excellent travail sur les fractions.",
            "date_survenue": aujourd_hui,
        },
        headers=ctx["enseignant_headers"],
    )
    assert entree.status_code == 201

    radar = client.get(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/radar-familial", headers=ctx["tuteur_headers"]
    )
    assert radar.status_code == 200
    assert len(radar.json()["sources"]) == 1
    assert "felicitation" in radar.json()["sources"][0]
    assert "Mathematiques" in radar.json()["sources"][0]


def test_radar_hors_periode_est_ignore(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_utilisateur_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    eleve_id = _eleve_id_de_la_classe(client, ctx)

    il_y_a_longtemps = (date.today() - timedelta(days=60)).isoformat()
    client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/eleves/{eleve_id}/vie-scolaire",
        json={
            "nature": "incident",
            "description": "Ancien incident hors periode.",
            "date_survenue": il_y_a_longtemps,
        },
        headers=ctx["enseignant_headers"],
    )

    radar = client.get(
        f"/api/v1/mes-enfants/{eleve_utilisateur_id}/radar-familial", headers=ctx["tuteur_headers"]
    )
    assert radar.status_code == 200
    assert radar.json()["sources"] == []


def test_radar_refuse_a_un_tuteur_qui_n_est_pas_le_sien(client, classe_avec_enseignant_et_eleve, fake_email_client):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]

    autre_tuteur_payload = {
        "nom": "Houngbo", "prenom": "Rita", "email": "rita.houngbo.radar@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=autre_tuteur_payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == autre_tuteur_payload["email"])
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": autre_tuteur_payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": autre_tuteur_payload["email"], "mot_de_passe": autre_tuteur_payload["mot_de_passe"]},
    ).json()
    autre_tuteur_headers = {"Authorization": f"Bearer {login['access_token']}"}

    refus = client.get(f"/api/v1/mes-enfants/{eleve_id}/radar-familial", headers=autre_tuteur_headers)
    assert refus.status_code == 403
