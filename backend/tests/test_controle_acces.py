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
