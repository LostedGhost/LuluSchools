import io

import pymupdf

from app.modules.recrutement.conversion import convertir_en_image


def test_convertir_en_image_transforme_un_pdf_en_png():
    document = pymupdf.open()
    document.new_page()
    pdf_bytes = document.tobytes()
    document.close()

    image_bytes, content_type = convertir_en_image(pdf_bytes, "application/pdf")

    assert content_type == "image/png"
    assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_convertir_en_image_laisse_passer_une_image_telle_quelle():
    image_bytes, content_type = convertir_en_image(b"contenu binaire", "image/png")
    assert image_bytes == b"contenu binaire"
    assert content_type == "image/png"


def _creer_poste(client, admin_headers, etablissement_id):
    return client.post(
        f"/api/v1/etablissements/{etablissement_id}/postes",
        json={
            "titre": "Professeur de mathematiques",
            "criteres": [
                {"type_document": "cv", "coefficient": 0.5, "seuil_minimal": 60},
                {"type_document": "diplome", "coefficient": 0.5, "seuil_minimal": 60},
            ],
        },
        headers=admin_headers,
    ).json()


def _postuler(client, enseignant_headers, poste_id, casier_bytes=b"casier"):
    return client.post(
        f"/api/v1/postes/{poste_id}/candidatures",
        data={"types": ["cv", "diplome"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"contenu cv"), "image/png")),
            ("fichiers", ("diplome.png", io.BytesIO(b"contenu diplome"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(casier_bytes), "application/pdf")),
        ],
        headers=enseignant_headers,
    )


def test_candidature_avec_scores_au_dessus_du_seuil_calcule_le_score(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.score_par_defaut = 80.0

    response = _postuler(client, enseignant_headers, poste["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 80.0
    assert body["statut"] == "en_evaluation"
    assert all(d["statut"] == "note" for d in body["documents"])


def test_candidature_sous_le_seuil_est_rejetee(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.scores_par_type = {"cv": 40.0, "diplome": 90.0}

    response = _postuler(client, enseignant_headers, poste["id"])
    assert response.status_code == 201
    assert response.json()["statut"] == "rejetee"


def test_candidature_avec_echec_notation_reste_en_evaluation_sans_score(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.types_en_echec = {"cv"}

    response = _postuler(client, enseignant_headers, poste["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["score"] is None
    assert body["statut"] == "en_evaluation"
    document_cv = next(d for d in body["documents"] if d["type_document"] == "cv")
    assert document_cv["statut"] == "echec_notation"


def test_documents_ne_correspondant_pas_aux_criteres_est_refuse(
    client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    response = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.pdf", io.BytesIO(b"contenu"), "application/pdf")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    )
    assert response.status_code == 422


def test_contestation_puis_acceptation_reintegre_la_candidature(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.scores_par_type = {"cv": 40.0, "diplome": 90.0}
    candidature = _postuler(client, enseignant_headers, poste["id"]).json()
    assert candidature["statut"] == "rejetee"

    contestation = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contestation",
        json={"motif": "Le CV a ete mal interprete"},
        headers=enseignant_headers,
    )
    assert contestation.status_code == 201

    decision = client.post(
        f"/api/v1/contestations/{contestation.json()['id']}/decision",
        json={"decision": "acceptee"},
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert decision.status_code == 200

    relue = client.get(f"/api/v1/candidatures/{candidature['id']}", headers=enseignant_headers)
    assert relue.json()["statut"] == "en_evaluation"


def test_contrat_puis_signature(client, fake_llm_client, enseignant_headers, etablissement_avec_classe):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.score_par_defaut = 85.0
    candidature = _postuler(client, enseignant_headers, poste["id"]).json()

    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme de mathematiques niveau CE1"},
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert contrat.status_code == 201
    contrat_id = contrat.json()["id"]

    signature_refusee = client.post(
        f"/api/v1/contrats/{contrat_id}/signer",
        json={"nom_tape": "Un Autre Nom"},
        headers=enseignant_headers,
    )
    assert signature_refusee.status_code == 422

    signature = client.post(
        f"/api/v1/contrats/{contrat_id}/signer",
        json={"nom_tape": "Moussa Traore"},
        headers=enseignant_headers,
    )
    assert signature.status_code == 200
    assert signature.json()["statut"] == "signe"


def test_casier_judiciaire_stocke_localement_pas_sur_lulufiles(
    client, fake_llm_client, fake_files_client, enseignant_headers, etablissement_avec_classe, tmp_path, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "casier_judiciaire_storage_path", str(tmp_path))
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])

    response = _postuler(client, enseignant_headers, poste["id"], casier_bytes=b"contenu sensible du casier")
    assert response.status_code == 201

    fichiers_ecrits = list(tmp_path.iterdir())
    assert len(fichiers_ecrits) == 1
    assert fichiers_ecrits[0].read_bytes() == b"contenu sensible du casier"
    # Seuls les 2 documents scores (cv, diplome) doivent avoir transite par LuluFiles.
    assert len(fake_files_client.uploaded) == 2
