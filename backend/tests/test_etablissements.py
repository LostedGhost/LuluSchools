PAYLOAD_ETABLISSEMENT = {
    "nom": "Ecole Primaire Sainte-Anne",
    "type": "EP",
    "statut": "public",
    "admin": {"nom": "Kone", "prenom": "Fatou", "email": "fatou.kone@example.com"},
    "latitude": 6.3703,
    "longitude": 2.3912,
}


def test_creation_etablissement_par_admin_ministeriel(client, fake_email_client, admin_ministeriel_headers):
    response = client.post(
        "/api/v1/etablissements", json=PAYLOAD_ETABLISSEMENT, headers=admin_ministeriel_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code_etablissement"] == "EP01"
    assert body["latitude"] == 6.3703
    assert body["longitude"] == 2.3912
    assert any(m["to_email"] == "fatou.kone@example.com" for m in fake_email_client.sent)


def test_creation_etablissement_refusee_sans_coordonnees(client, admin_ministeriel_headers):
    payload_sans_coordonnees = {k: v for k, v in PAYLOAD_ETABLISSEMENT.items() if k not in ("latitude", "longitude")}
    response = client.post(
        "/api/v1/etablissements", json=payload_sans_coordonnees, headers=admin_ministeriel_headers
    )
    assert response.status_code == 422


def test_mise_a_jour_localisation(client, fake_email_client, admin_ministeriel_headers):
    etablissement = client.post(
        "/api/v1/etablissements", json=PAYLOAD_ETABLISSEMENT, headers=admin_ministeriel_headers
    ).json()

    mise_a_jour = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/localisation",
        json={"latitude": 9.3372, "longitude": 2.6288},
        headers=admin_ministeriel_headers,
    )
    assert mise_a_jour.status_code == 200
    assert mise_a_jour.json()["latitude"] == 9.3372
    assert mise_a_jour.json()["longitude"] == 2.6288


def test_mise_a_jour_localisation_refusee_pour_non_admin_ministeriel(client, fake_email_client, admin_ministeriel_headers):
    etablissement = client.post(
        "/api/v1/etablissements", json=PAYLOAD_ETABLISSEMENT, headers=admin_ministeriel_headers
    ).json()
    client.post("/api/v1/auth/tuteurs", json={
        "nom": "Dossou", "prenom": "Awa", "email": "awa.tuteur.geoloc@example.com", "mot_de_passe": "Password1",
    })
    code = fake_email_client.sent[-1]["code"]
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": "awa.tuteur.geoloc@example.com", "code": code})
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": "awa.tuteur.geoloc@example.com", "mot_de_passe": "Password1"}
    ).json()
    tuteur_headers = {"Authorization": f"Bearer {login['access_token']}"}

    refus = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/localisation",
        json={"latitude": 9.3372, "longitude": 2.6288},
        headers=tuteur_headers,
    )
    assert refus.status_code == 403


def test_creation_etablissement_refusee_pour_non_admin_ministeriel(client, fake_email_client):
    client.post("/api/v1/auth/tuteurs", json={
        "nom": "Dossou", "prenom": "Awa", "email": "awa.tuteur@example.com", "mot_de_passe": "Password1",
    })
    code = fake_email_client.sent[-1]["code"]
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": "awa.tuteur@example.com", "code": code})
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": "awa.tuteur@example.com", "mot_de_passe": "Password1"}
    ).json()

    response = client.post(
        "/api/v1/etablissements",
        json=PAYLOAD_ETABLISSEMENT,
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert response.status_code == 403


def test_codes_etablissement_incrementent_par_type(client, admin_ministeriel_headers):
    premier = client.post(
        "/api/v1/etablissements", json=PAYLOAD_ETABLISSEMENT, headers=admin_ministeriel_headers
    ).json()
    deuxieme_payload = {
        **PAYLOAD_ETABLISSEMENT,
        "admin": {"nom": "Kone", "prenom": "Issa", "email": "issa.kone@example.com"},
    }
    deuxieme = client.post(
        "/api/v1/etablissements", json=deuxieme_payload, headers=admin_ministeriel_headers
    ).json()
    assert premier["code_etablissement"] == "EP01"
    assert deuxieme["code_etablissement"] == "EP02"


def test_admin_etablissement_peut_creer_une_classe_dans_son_etablissement(
    client, fake_email_client, admin_ministeriel_headers
):
    etablissement = client.post(
        "/api/v1/etablissements", json=PAYLOAD_ETABLISSEMENT, headers=admin_ministeriel_headers
    ).json()
    mot_de_passe_temp = fake_email_client.sent[-1]["mot_de_passe"]
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "fatou.kone@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    assert login["doit_changer_mot_de_passe"] is True
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    refus_avant_changement = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "CE1", "capacite": 30, "politique_depassement": "ordre_arrivee"},
        headers=headers,
    )
    assert refus_avant_changement.status_code == 403
    assert refus_avant_changement.json()["error"]["code"] == "changement_mot_de_passe_requis"

    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mot_de_passe_temp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=headers,
    )

    response = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "CE1", "capacite": 30, "politique_depassement": "ordre_arrivee"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["etablissement_id"] == etablissement["id"]

    mon_etab = client.get("/api/v1/etablissements/mon-etablissement", headers=headers)
    assert mon_etab.status_code == 200
    assert mon_etab.json()["id"] == etablissement["id"]


def test_admin_etablissement_ne_peut_pas_creer_une_classe_ailleurs(
    client, fake_email_client, admin_ministeriel_headers
):
    etablissement_1 = client.post(
        "/api/v1/etablissements", json=PAYLOAD_ETABLISSEMENT, headers=admin_ministeriel_headers
    ).json()
    payload_2 = {
        **PAYLOAD_ETABLISSEMENT,
        "admin": {"nom": "Traore", "prenom": "Ali", "email": "ali.traore@example.com"},
    }
    etablissement_2 = client.post(
        "/api/v1/etablissements", json=payload_2, headers=admin_ministeriel_headers
    ).json()

    mot_de_passe_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m["to_email"] == "ali.traore@example.com"
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "ali.traore@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    response = client.post(
        f"/api/v1/etablissements/{etablissement_1['id']}/classes",
        json={"niveau": "CE1", "capacite": 30, "politique_depassement": "ordre_arrivee"},
        headers=headers,
    )
    assert response.status_code == 403


def _provisionner_admin_etablissement(client, fake_email_client, admin_ministeriel_headers, payload, email):
    etablissement = client.post(
        "/api/v1/etablissements", json=payload, headers=admin_ministeriel_headers
    ).json()
    mot_de_passe_temp = next(m["mot_de_passe"] for m in fake_email_client.sent if m["to_email"] == email)
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": email, "mot_de_passe": mot_de_passe_temp}
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mot_de_passe_temp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=headers,
    )
    return etablissement, headers


def test_admin_etablissement_peut_mettre_a_jour_sa_propre_localisation(
    client, fake_email_client, admin_ministeriel_headers
):
    payload = {**PAYLOAD_ETABLISSEMENT, "admin": {"nom": "Kone", "prenom": "Fatou", "email": "fatou.kone.geoloc@example.com"}}
    etablissement, headers = _provisionner_admin_etablissement(
        client, fake_email_client, admin_ministeriel_headers, payload, "fatou.kone.geoloc@example.com"
    )

    mise_a_jour = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/localisation",
        json={"latitude": 9.3372, "longitude": 2.6288},
        headers=headers,
    )
    assert mise_a_jour.status_code == 200
    assert mise_a_jour.json()["latitude"] == 9.3372


def test_admin_etablissement_ne_peut_pas_mettre_a_jour_la_localisation_d_un_autre(
    client, fake_email_client, admin_ministeriel_headers
):
    payload_1 = {**PAYLOAD_ETABLISSEMENT, "admin": {"nom": "Kone", "prenom": "Fatou", "email": "fatou.kone.geoloc2@example.com"}}
    etablissement_1, _ = _provisionner_admin_etablissement(
        client, fake_email_client, admin_ministeriel_headers, payload_1, "fatou.kone.geoloc2@example.com"
    )
    payload_2 = {**PAYLOAD_ETABLISSEMENT, "admin": {"nom": "Traore", "prenom": "Ali", "email": "ali.traore.geoloc@example.com"}}
    _, headers_2 = _provisionner_admin_etablissement(
        client, fake_email_client, admin_ministeriel_headers, payload_2, "ali.traore.geoloc@example.com"
    )

    refus = client.post(
        f"/api/v1/etablissements/{etablissement_1['id']}/localisation",
        json={"latitude": 9.3372, "longitude": 2.6288},
        headers=headers_2,
    )
    assert refus.status_code == 403
