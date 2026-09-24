PAYLOAD_VALIDE = {
    "nom": "Dossou",
    "prenom": "Awa",
    "email": "awa.dossou@example.com",
    "mot_de_passe": "Password1",
}


def test_creation_compte_envoie_un_otp_par_email(client, fake_email_client):
    response = client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == PAYLOAD_VALIDE["email"]
    assert body["email_verifie"] is False
    assert len(fake_email_client.sent) == 1
    assert fake_email_client.sent[0]["to_email"] == PAYLOAD_VALIDE["email"]
    assert len(fake_email_client.sent[0]["code"]) == 6


def test_creation_compte_refuse_email_deja_utilise(client):
    premiere = client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)
    assert premiere.status_code == 201

    seconde = client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)
    assert seconde.status_code == 409
    assert seconde.json()["error"]["code"] == "email_deja_utilise"


def test_creation_compte_refuse_mot_de_passe_faible(client):
    payload = {**PAYLOAD_VALIDE, "mot_de_passe": "abc"}
    response = client.post("/api/v1/auth/tuteurs", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_creation_compte_rejette_champ_non_prevu(client):
    payload = {**PAYLOAD_VALIDE, "role": "admin_ministeriel"}
    response = client.post("/api/v1/auth/tuteurs", json=payload)
    assert response.status_code == 422


def test_echec_envoi_email_annule_la_creation_du_compte(client, fake_email_client):
    fake_email_client.should_fail = True
    response = client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "envoi_email_echoue"

    fake_email_client.should_fail = False
    retry = client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)
    assert retry.status_code == 201


def test_verification_otp_avec_le_bon_code_active_le_compte(client, fake_email_client):
    client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)
    code = fake_email_client.sent[0]["code"]

    response = client.post(
        "/api/v1/auth/tuteurs/verify-otp",
        json={"email": PAYLOAD_VALIDE["email"], "code": code},
    )
    assert response.status_code == 200
    assert response.json() == {"email": PAYLOAD_VALIDE["email"], "email_verifie": True}


def test_verification_otp_avec_mauvais_code_est_rejetee(client, fake_email_client):
    client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)
    vrai_code = fake_email_client.sent[0]["code"]
    mauvais_code = "".join("1" if c == "0" else "0" for c in vrai_code)

    response = client.post(
        "/api/v1/auth/tuteurs/verify-otp",
        json={"email": PAYLOAD_VALIDE["email"], "code": mauvais_code},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "otp_invalide"


def test_verification_otp_epuise_les_tentatives_apres_cinq_echecs(client, fake_email_client):
    client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)
    vrai_code = fake_email_client.sent[0]["code"]
    mauvais_code = "".join("1" if c == "0" else "0" for c in vrai_code)

    for _ in range(5):
        response = client.post(
            "/api/v1/auth/tuteurs/verify-otp",
            json={"email": PAYLOAD_VALIDE["email"], "code": mauvais_code},
        )
        assert response.status_code == 401

    derniere_tentative = client.post(
        "/api/v1/auth/tuteurs/verify-otp",
        json={"email": PAYLOAD_VALIDE["email"], "code": vrai_code},
    )
    assert derniere_tentative.status_code == 400
    assert derniere_tentative.json()["error"]["code"] == "otp_tentatives_epuisees"


def test_verification_otp_deja_verifie_est_un_conflit(client, fake_email_client):
    client.post("/api/v1/auth/tuteurs", json=PAYLOAD_VALIDE)
    code = fake_email_client.sent[0]["code"]
    client.post(
        "/api/v1/auth/tuteurs/verify-otp", json={"email": PAYLOAD_VALIDE["email"], "code": code}
    )

    response = client.post(
        "/api/v1/auth/tuteurs/verify-otp", json={"email": PAYLOAD_VALIDE["email"], "code": code}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "deja_verifie"


def test_verification_otp_compte_introuvable(client):
    response = client.post(
        "/api/v1/auth/tuteurs/verify-otp",
        json={"email": "inconnu@example.com", "code": "123456"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "compte_introuvable"
