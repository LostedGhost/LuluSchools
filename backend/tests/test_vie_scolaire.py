"""UC-23 : vie scolaire - portee de lecture/ecriture (professeur principal vs enseignant
de matiere ordinaire), historique immuable (pas de PATCH/DELETE expose)."""

import io


def _affecter_comme_professeur_principal(client, admin_headers, classe_id, enseignant_utilisateur_id):
    reponse = client.post(
        f"/api/v1/classes/{classe_id}/professeur-principal",
        json={"enseignant_utilisateur_id": enseignant_utilisateur_id},
        headers=admin_headers,
    )
    assert reponse.status_code == 200
    return reponse.json()


def _provisionner_second_enseignant_affecte(client, fake_email_client, fake_llm_client, ctx, email):
    """Deuxieme enseignant, sous contrat ET affecte a la meme classe que celui de
    `classe_avec_enseignant_et_eleve` - sert aux scenarios multi-enseignants (portee
    "sa matiere" vs professeur principal)."""
    admin_headers = ctx["admin_headers"]
    etablissement_id = ctx["etablissement"]["id"]
    classe_id = ctx["classe"]["id"]

    client.post(
        "/api/v1/auth/enseignants",
        json={"nom": "Boko", "prenom": "Chantal", "email": email, "mot_de_passe": "Password1"},
    )
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == email)
    client.post("/api/v1/auth/enseignants/verify-otp", json={"email": email, "code": code})
    login = client.post("/api/v1/auth/login", json={"identifiant": email, "mot_de_passe": "Password1"}).json()
    enseignant_headers = {"Authorization": f"Bearer {login['access_token']}"}

    poste = client.post(
        f"/api/v1/etablissements/{etablissement_id}/postes",
        json={"titre": "Professeur", "criteres": [{"type_document": "cv", "coefficient": 1, "seuil_minimal": 0}]},
        headers=admin_headers,
    ).json()
    fake_llm_client.score_par_defaut = 100.0
    candidature = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"contenu"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    ).json()
    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme", "date_fin": "2027-06-30"},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/contrats/{contrat['id']}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace"), "image/png")},
        headers=enseignant_headers,
    )
    from app.core.security import decode_token

    enseignant_utilisateur_id = decode_token(enseignant_headers["Authorization"].split(" ")[1])["sub"]
    client.post(
        f"/api/v1/classes/{classe_id}/affectations",
        json={"enseignant_utilisateur_id": enseignant_utilisateur_id},
        headers=admin_headers,
    )
    return enseignant_headers, enseignant_utilisateur_id


def _eleve_id_de(ctx, client):
    eleves = client.get(f"/api/v1/classes/{ctx['classe']['id']}/eleves", headers=ctx["admin_headers"]).json()
    return eleves[0]["eleve_id"]


def test_enseignant_cree_et_lit_sa_propre_entree(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = _eleve_id_de(ctx, client)

    creation = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/eleves/{eleve_id}/vie-scolaire",
        json={"nature": "absence", "matiere": "Mathematiques", "description": "Absent le 10/09, non justifie."},
        headers=ctx["enseignant_headers"],
    )
    assert creation.status_code == 201
    assert creation.json()["matiere"] == "Mathematiques"

    liste = client.get(
        f"/api/v1/classes/{ctx['classe']['id']}/eleves/{eleve_id}/vie-scolaire", headers=ctx["enseignant_headers"]
    ).json()
    assert len(liste) == 1


def test_enseignant_de_matiere_sans_matiere_precisee_est_refuse(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = _eleve_id_de(ctx, client)

    reponse = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/eleves/{eleve_id}/vie-scolaire",
        json={"nature": "appreciation", "description": "Bon trimestre."},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.status_code == 422


def test_professeur_principal_voit_tout_enseignant_de_matiere_ne_voit_que_le_sien(
    client, fake_email_client, fake_llm_client, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    classe_id = ctx["classe"]["id"]
    eleve_id = _eleve_id_de(ctx, client)

    from app.core.security import decode_token

    premier_enseignant_id = decode_token(ctx["enseignant_headers"]["Authorization"].split(" ")[1])["sub"]
    _affecter_comme_professeur_principal(client, ctx["admin_headers"], classe_id, premier_enseignant_id)

    second_headers, _ = _provisionner_second_enseignant_affecte(
        client, fake_email_client, fake_llm_client, ctx, "chantal.boko.viescolaire@example.com"
    )

    # Le professeur principal consigne une entree globale (sans matiere).
    client.post(
        f"/api/v1/classes/{classe_id}/eleves/{eleve_id}/vie-scolaire",
        json={"nature": "appreciation", "description": "Eleve serieux en general."},
        headers=ctx["enseignant_headers"],
    )
    # Le second enseignant consigne dans sa propre matiere.
    client.post(
        f"/api/v1/classes/{classe_id}/eleves/{eleve_id}/vie-scolaire",
        json={"nature": "incident", "matiere": "SVT", "description": "Bavardages en cours."},
        headers=second_headers,
    )

    vue_pp = client.get(
        f"/api/v1/classes/{classe_id}/eleves/{eleve_id}/vie-scolaire", headers=ctx["enseignant_headers"]
    ).json()
    assert len(vue_pp) == 2

    vue_second = client.get(
        f"/api/v1/classes/{classe_id}/eleves/{eleve_id}/vie-scolaire", headers=second_headers
    ).json()
    assert len(vue_second) == 1
    assert vue_second[0]["matiere"] == "SVT"


def test_tuteur_et_eleve_voient_toute_la_vie_scolaire(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    classe_id = ctx["classe"]["id"]
    eleve_id = _eleve_id_de(ctx, client)

    client.post(
        f"/api/v1/classes/{classe_id}/eleves/{eleve_id}/vie-scolaire",
        json={"nature": "retard", "matiere": "Mathematiques", "description": "10 minutes de retard."},
        headers=ctx["enseignant_headers"],
    )

    for headers in (ctx["tuteur_headers"], ctx["eleve_headers"]):
        vue = client.get(
            f"/api/v1/classes/{classe_id}/eleves/{eleve_id}/vie-scolaire", headers=headers
        ).json()
        assert len(vue) == 1


def test_vue_de_classe_entiere_reservee_a_ladministration_et_au_professeur_principal(
    client, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    classe_id = ctx["classe"]["id"]

    refuse = client.get(f"/api/v1/classes/{classe_id}/vie-scolaire", headers=ctx["enseignant_headers"])
    assert refuse.status_code == 403

    autorise_admin = client.get(f"/api/v1/classes/{classe_id}/vie-scolaire", headers=ctx["admin_headers"])
    assert autorise_admin.status_code == 200


def test_entree_vie_scolaire_refusee_pour_eleve_hors_classe(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    reponse = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/eleves/id-inexistant/vie-scolaire",
        json={"nature": "absence", "matiere": "Mathematiques", "description": "Absent."},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.status_code == 404
