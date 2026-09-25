from datetime import date


def _date_naissance_pour_age(age: int) -> str:
    aujourd_hui = date.today()
    return date(aujourd_hui.year - age, aujourd_hui.month, 1).isoformat()


def test_inscription_mineur_sans_consentement_reste_en_attente(
    client, tuteur_headers, etablissement_avec_classe
):
    response = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Kofi",
            "date_naissance": _date_naissance_pour_age(10),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    )
    assert response.status_code == 201
    assert response.json()["statut"] == "en_attente_consentement_parental"


def test_inscription_mineur_avec_consentement_immediat_est_soumise(
    client, tuteur_headers, etablissement_avec_classe
):
    response = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Kofi",
            "date_naissance": _date_naissance_pour_age(10),
            "classe_id": etablissement_avec_classe["classe"]["id"],
            "consentement_parental_donne": True,
        },
        headers=tuteur_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["statut"] == "soumise"
    assert body["consentement_parental_horodatage"] is not None


def test_inscription_majeur_est_directement_soumise(client, tuteur_headers, etablissement_avec_classe):
    response = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Aisha",
            "date_naissance": _date_naissance_pour_age(17),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    )
    assert response.status_code == 201
    assert response.json()["statut"] == "soumise"


def test_donner_consentement_parental_debloque_l_inscription(
    client, tuteur_headers, etablissement_avec_classe
):
    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Kofi",
            "date_naissance": _date_naissance_pour_age(10),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    ).json()

    response = client.post(
        f"/api/v1/inscriptions/{inscription['id']}/consentement-parental", headers=tuteur_headers
    )
    assert response.status_code == 200
    assert response.json()["statut"] == "soumise"


def test_validation_genere_un_matricule_et_envoie_les_identifiants(
    client, fake_email_client, tuteur_headers, etablissement_avec_classe
):
    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Aisha",
            "date_naissance": _date_naissance_pour_age(17),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    ).json()

    response = client.post(
        f"/api/v1/inscriptions/{inscription['id']}/valider",
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert response.status_code == 200
    assert response.json()["statut"] == "validee"
    assert any("mot_de_passe" in m and "login_id" in m for m in fake_email_client.sent)


def test_validation_refusee_si_classe_complete(
    client, fake_email_client, tuteur_headers, etablissement_avec_classe
):
    # La classe de la fixture a une capacite de 1.
    premiere = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Aisha",
            "date_naissance": _date_naissance_pour_age(17),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    ).json()
    client.post(
        f"/api/v1/inscriptions/{premiere['id']}/valider",
        headers=etablissement_avec_classe["admin_headers"],
    )

    seconde = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Ibrahim",
            "date_naissance": _date_naissance_pour_age(17),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    ).json()
    response = client.post(
        f"/api/v1/inscriptions/{seconde['id']}/valider",
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "classe_complete"


def test_validation_refusee_sans_consentement_parental(
    client, tuteur_headers, etablissement_avec_classe
):
    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Kofi",
            "date_naissance": _date_naissance_pour_age(10),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    ).json()

    response = client.post(
        f"/api/v1/inscriptions/{inscription['id']}/valider",
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "consentement_manquant"


def test_rejet_inscription_avec_motif(client, tuteur_headers, etablissement_avec_classe):
    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Aisha",
            "date_naissance": _date_naissance_pour_age(17),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    ).json()

    response = client.post(
        f"/api/v1/inscriptions/{inscription['id']}/rejeter",
        json={"motif": "Dossier incomplet"},
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert response.status_code == 200
    assert response.json()["statut"] == "rejetee"
    assert response.json()["motif_rejet"] == "Dossier incomplet"


def test_eleve_connecte_avec_son_matricule(client, fake_email_client, tuteur_headers, etablissement_avec_classe):
    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Aisha",
            "date_naissance": _date_naissance_pour_age(17),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    ).json()
    client.post(
        f"/api/v1/inscriptions/{inscription['id']}/valider",
        headers=etablissement_avec_classe["admin_headers"],
    )
    identifiants = next(m for m in reversed(fake_email_client.sent) if "login_id" in m)

    response = client.post(
        "/api/v1/auth/login",
        json={"identifiant": identifiants["login_id"], "mot_de_passe": identifiants["mot_de_passe"]},
    )
    assert response.status_code == 200
    assert response.json()["doit_changer_mot_de_passe"] is True


def test_eleve_titulaire_peut_soumettre_sa_propre_reinscription(
    client, fake_email_client, tuteur_headers, etablissement_avec_classe
):
    premiere = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Aisha",
            "date_naissance": _date_naissance_pour_age(17),
            "classe_id": etablissement_avec_classe["classe"]["id"],
        },
        headers=tuteur_headers,
    ).json()
    client.post(
        f"/api/v1/inscriptions/{premiere['id']}/valider",
        headers=etablissement_avec_classe["admin_headers"],
    )
    identifiants = next(m for m in reversed(fake_email_client.sent) if "login_id" in m)
    login_eleve = client.post(
        "/api/v1/auth/login",
        json={"identifiant": identifiants["login_id"], "mot_de_passe": identifiants["mot_de_passe"]},
    ).json()
    eleve_headers = {"Authorization": f"Bearer {login_eleve['access_token']}"}

    # Nouvelle classe (celle de la fixture est deja a capacite max avec la premiere inscription).
    nouvelle_classe = client.post(
        f"/api/v1/etablissements/{etablissement_avec_classe['etablissement']['id']}/classes",
        json={"niveau": "CE2", "capacite": 5, "politique_depassement": "ordre_arrivee"},
        headers=etablissement_avec_classe["admin_headers"],
    ).json()

    reinscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Dossou",
            "prenom": "Aisha",
            "date_naissance": _date_naissance_pour_age(17),
            "classe_id": nouvelle_classe["id"],
        },
        headers=eleve_headers,
    )
    assert reinscription.status_code == 201
    assert reinscription.json()["statut"] == "soumise"


def test_tuteur_non_habilite_ne_peut_pas_soumettre_une_demande_sans_lien(
    client, admin_ministeriel_headers
):
    response = client.post(
        "/api/v1/inscriptions",
        json={"nom": "X", "prenom": "Y", "date_naissance": "2010-01-01", "classe_id": "inexistante"},
        headers=admin_ministeriel_headers,
    )
    assert response.status_code == 403
