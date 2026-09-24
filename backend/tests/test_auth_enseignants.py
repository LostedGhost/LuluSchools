PAYLOAD_VALIDE = {
    "nom": "Traore",
    "prenom": "Moussa",
    "email": "moussa.traore@example.com",
    "mot_de_passe": "Password1",
}


def test_creation_compte_enseignant_envoie_un_otp(client, fake_email_client):
    response = client.post("/api/v1/auth/enseignants", json=PAYLOAD_VALIDE)
    assert response.status_code == 201
    assert response.json()["email_verifie"] is False
    assert len(fake_email_client.sent) == 1


def test_verification_otp_enseignant_active_le_compte_et_permet_le_login(client, fake_email_client):
    client.post("/api/v1/auth/enseignants", json=PAYLOAD_VALIDE)
    code = fake_email_client.sent[-1]["code"]
    verify = client.post(
        "/api/v1/auth/enseignants/verify-otp", json={"email": PAYLOAD_VALIDE["email"], "code": code}
    )
    assert verify.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": PAYLOAD_VALIDE["email"], "mot_de_passe": PAYLOAD_VALIDE["mot_de_passe"]},
    )
    assert login.status_code == 200
