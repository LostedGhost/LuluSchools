def test_admin_designe_un_controleur_transport(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]

    response = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "transport"},
        headers=ctx["admin_headers"],
    )
    assert response.status_code == 201
    assert response.json()["service"] == "transport"
    assert response.json()["evenement_id"] is None


def test_designation_evenement_exige_evenement_id(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]

    sans_evenement = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "evenement"},
        headers=ctx["admin_headers"],
    )
    assert sans_evenement.status_code == 422

    avec_evenement = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "evenement", "evenement_id": "evt-1"},
        headers=ctx["admin_headers"],
    )
    assert avec_evenement.status_code == 201

    # evenement_id fourni pour un service autre que "evenement" est tout aussi invalide.
    incoherent = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "cantine", "evenement_id": "evt-1"},
        headers=ctx["admin_headers"],
    )
    assert incoherent.status_code == 422


def test_seul_admin_de_l_etablissement_peut_designer(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]

    response = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "cantine"},
        headers=ctx["enseignant_headers"],
    )
    assert response.status_code == 403


def test_lister_et_revoquer_une_designation(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]

    designation = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "cantine"},
        headers=ctx["admin_headers"],
    ).json()

    liste = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs", headers=ctx["admin_headers"]
    )
    assert liste.status_code == 200
    assert len(liste.json()) == 1

    suppression = client.delete(f"/api/v1/controleurs/{designation['id']}", headers=ctx["admin_headers"])
    assert suppression.status_code == 204

    liste_apres = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs", headers=ctx["admin_headers"]
    )
    assert liste_apres.json() == []


def test_recherche_utilisateurs_designables_par_nom(client, classe_avec_enseignant_et_eleve):
    """UC-28 : remplace la saisie d'un id brut - propose les enseignants sous contrat
    signe et les admins de l'etablissement, filtres par nom/prenom."""
    ctx = classe_avec_enseignant_et_eleve
    etablissement_id = ctx["etablissement"]["id"]

    trouve = client.get(
        f"/api/v1/etablissements/{etablissement_id}/utilisateurs-designables",
        params={"q": "traore"},
        headers=ctx["admin_headers"],
    ).json()
    assert len(trouve) == 1
    assert trouve[0]["nom"] == "Traore"
    assert trouve[0]["role"] == "enseignant"

    introuvable = client.get(
        f"/api/v1/etablissements/{etablissement_id}/utilisateurs-designables",
        params={"q": "personne-de-ce-nom"},
        headers=ctx["admin_headers"],
    ).json()
    assert introuvable == []

    sans_filtre = client.get(
        f"/api/v1/etablissements/{etablissement_id}/utilisateurs-designables", headers=ctx["admin_headers"]
    ).json()
    # L'enseignant sous contrat ET l'admin de l'etablissement lui-meme sont proposables.
    assert len(sans_filtre) == 2


def test_recherche_utilisateurs_designables_refusee_pour_un_autre_etablissement(
    client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers, fake_email_client
):
    ctx = classe_avec_enseignant_et_eleve
    autre = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Ecole Etrangere Controleur",
            "type": "EP",
            "statut": "public",
            "admin": {"nom": "Adjovi", "prenom": "Rose", "email": "rose.adjovi.controleur@example.com"},
            "latitude": 6.4969,
            "longitude": 2.6289,
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "rose.adjovi.controleur@example.com"
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "rose.adjovi.controleur@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    headers_etranger = {"Authorization": f"Bearer {login['access_token']}"}

    reponse = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/utilisateurs-designables", headers=headers_etranger
    )
    assert reponse.status_code == 403
