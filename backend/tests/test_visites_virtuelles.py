def test_admin_etablissement_publie_une_visite_avec_attestation(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    reponse = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/visites-virtuelles",
        json={"type": "3d", "lien_externe": "https://matterport.example.com/tour", "attestation_autorisation": True},
        headers=ctx["admin_headers"],
    )
    assert reponse.status_code == 201
    assert reponse.json()["type"] == "3d"


def test_attestation_manquante_est_refusee(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    reponse = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/visites-virtuelles",
        json={"type": "drone", "lien_externe": "https://video.example.com/drone", "attestation_autorisation": False},
        headers=ctx["admin_headers"],
    )
    assert reponse.status_code == 422


def test_admin_ministeriel_peut_publier_pour_n_importe_quel_etablissement(
    client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    reponse = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/visites-virtuelles",
        json={"type": "drone", "lien_externe": "https://video.example.com/drone", "attestation_autorisation": True},
        headers=admin_ministeriel_headers,
    )
    assert reponse.status_code == 201


def test_enseignant_ne_peut_pas_publier_ni_retirer(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    refus = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/visites-virtuelles",
        json={"type": "3d", "lien_externe": "https://matterport.example.com/tour", "attestation_autorisation": True},
        headers=ctx["enseignant_headers"],
    )
    assert refus.status_code == 403


def test_lister_et_retirer_une_visite(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    visite = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/visites-virtuelles",
        json={"type": "3d", "lien_externe": "https://matterport.example.com/tour", "attestation_autorisation": True},
        headers=ctx["admin_headers"],
    ).json()

    liste = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/visites-virtuelles", headers=ctx["eleve_headers"]
    )
    assert len(liste.json()) == 1

    suppression = client.delete(f"/api/v1/visites-virtuelles/{visite['id']}", headers=ctx["admin_headers"])
    assert suppression.status_code == 204

    liste_apres = client.get(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/visites-virtuelles", headers=ctx["eleve_headers"]
    )
    assert liste_apres.json() == []
