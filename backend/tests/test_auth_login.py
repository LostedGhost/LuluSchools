PAYLOAD_VALIDE = {
    "nom": "Dossou",
    "prenom": "Awa",
    "email": "awa.login@example.com",
    "mot_de_passe": "Password1",
}


def _creer_et_verifier_compte(client, fake_email_client, payload=None):
    payload = payload or PAYLOAD_VALIDE
    client.post("/api/v1/auth/tuteurs", json=payload)
    code = fake_email_client.sent[-1]["code"]
    client.post(
        "/api/v1/auth/tuteurs/verify-otp", json={"email": payload["email"], "code": code}
    )
    return payload


def test_login_avec_bon_mot_de_passe_renvoie_des_tokens(client, fake_email_client):
    payload = _creer_et_verifier_compte(client, fake_email_client)

    response = client.post(
        "/api/v1/auth/login",
        json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["doit_changer_mot_de_passe"] is False


def test_login_refuse_avant_verification_email(client, fake_email_client):
    client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)

    response = client.post(
        "/api/v1/auth/login",
        json={"identifiant": PAYLOAD_VALIDE["email"], "mot_de_passe": PAYLOAD_VALIDE["mot_de_passe"]},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "compte_non_verifie"


def test_login_refuse_mauvais_mot_de_passe(client, fake_email_client):
    payload = _creer_et_verifier_compte(client, fake_email_client)

    response = client.post(
        "/api/v1/auth/login",
        json={"identifiant": payload["email"], "mot_de_passe": "MauvaisMotDePasse1"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "identifiants_invalides"


def test_refresh_token_renvoie_une_nouvelle_paire(client, fake_email_client):
    payload = _creer_et_verifier_compte(client, fake_email_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]},
    ).json()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_avec_un_access_token_est_refuse(client, fake_email_client):
    payload = _creer_et_verifier_compte(client, fake_email_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]},
    ).json()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": login["access_token"]})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_invalide"


def test_me_sans_token_est_refuse(client):
    response = client.get("/api/v1/me")
    assert response.status_code == 401


def test_me_avec_token_renvoie_le_profil(client, fake_email_client):
    payload = _creer_et_verifier_compte(client, fake_email_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]},
    ).json()

    response = client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {login['access_token']}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == payload["email"]
    assert body["role"] == "tuteur"


def test_changer_mot_de_passe(client, fake_email_client):
    payload = _creer_et_verifier_compte(client, fake_email_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    response = client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": payload["mot_de_passe"], "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=headers,
    )
    assert response.status_code == 200

    ancien = client.post(
        "/api/v1/auth/login",
        json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]},
    )
    assert ancien.status_code == 401

    nouveau = client.post(
        "/api/v1/auth/login", json={"identifiant": payload["email"], "mot_de_passe": "NouveauMdp1"}
    )
    assert nouveau.status_code == 200
