import io
from datetime import date, timedelta

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


def _postuler_et_relire(client, enseignant_headers, poste_id, casier_bytes=b"casier"):
    """La notation IA part desormais en arriere-plan (BackgroundTasks) : la reponse de
    POST reflete l'etat juste avant traitement (documents en_attente). Le test relit la
    candidature ensuite pour observer le resultat une fois la notation terminee (avec
    TestClient, la tache d'arriere-plan s'execute avant que ce GET ne soit atteint)."""
    response = _postuler(client, enseignant_headers, poste_id, casier_bytes)
    assert response.status_code == 201
    candidature_id = response.json()["id"]
    return client.get(f"/api/v1/candidatures/{candidature_id}", headers=enseignant_headers)


def test_candidature_avec_scores_au_dessus_du_seuil_calcule_le_score(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.score_par_defaut = 80.0

    body = _postuler_et_relire(client, enseignant_headers, poste["id"]).json()
    assert body["score"] == 80.0
    assert body["statut"] == "en_evaluation"
    assert all(d["statut"] == "note" for d in body["documents"])


def test_candidature_sous_le_seuil_est_rejetee(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.scores_par_type = {"cv": 40.0, "diplome": 90.0}

    body = _postuler_et_relire(client, enseignant_headers, poste["id"]).json()
    assert body["statut"] == "rejetee"


def test_candidature_avec_echec_notation_reste_en_evaluation_sans_score(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.types_en_echec = {"cv"}

    body = _postuler_et_relire(client, enseignant_headers, poste["id"]).json()
    assert body["score"] is None
    assert body["statut"] == "en_evaluation"
    document_cv = next(d for d in body["documents"] if d["type_document"] == "cv")
    assert document_cv["statut"] == "echec_notation"

    # Le document doit exposer son id : sans lui, l'ecran de revision manuelle
    # (POST /documents-candidature/{id}/noter-manuellement) est inutilisable.
    revision = client.post(
        f"/api/v1/documents-candidature/{document_cv['id']}/noter-manuellement",
        json={"note": 90},
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert revision.status_code == 200
    assert revision.json()["score"] is not None


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
    candidature = _postuler_et_relire(client, enseignant_headers, poste["id"]).json()
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
        json={
            "syllabus": "Programme de mathematiques niveau CE1",
            "date_fin": (date.today() + timedelta(days=300)).isoformat(),
        },
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert contrat.status_code == 201
    contrat_id = contrat.json()["id"]

    signature_vide = client.post(
        f"/api/v1/contrats/{contrat_id}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b""), "image/png")},
        headers=enseignant_headers,
    )
    assert signature_vide.status_code == 422

    signature = client.post(
        f"/api/v1/contrats/{contrat_id}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace-du-canvas-en-png"), "image/png")},
        headers=enseignant_headers,
    )
    assert signature.status_code == 200
    assert signature.json()["signature_image_lulufiles_id"] is not None
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


def _creer_contrat_signe(client, fake_llm_client, enseignant_headers, etablissement_avec_classe, date_fin):
    poste = _creer_poste(
        client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"]
    )
    fake_llm_client.score_par_defaut = 85.0
    candidature = _postuler(client, enseignant_headers, poste["id"]).json()
    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme initial", "date_fin": date_fin.isoformat()},
        headers=etablissement_avec_classe["admin_headers"],
    ).json()
    client.post(
        f"/api/v1/contrats/{contrat['id']}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace-du-canvas-en-png"), "image/png")},
        headers=enseignant_headers,
    )
    return contrat


def test_reconduction_refusee_hors_fenetre(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    contrat = _creer_contrat_signe(
        client, fake_llm_client, enseignant_headers, etablissement_avec_classe, date.today() + timedelta(days=200)
    )

    response = client.post(
        f"/api/v1/contrats/{contrat['id']}/reconduction",
        json={"syllabus": "Programme reconduit", "date_fin": (date.today() + timedelta(days=565)).isoformat()},
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "hors_fenetre"


def test_reconduction_dans_la_fenetre_cree_un_nouveau_contrat_a_signer(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    contrat = _creer_contrat_signe(
        client, fake_llm_client, enseignant_headers, etablissement_avec_classe, date.today() + timedelta(days=20)
    )

    proposition = client.post(
        f"/api/v1/contrats/{contrat['id']}/reconduction",
        json={"syllabus": "Programme reconduit", "date_fin": (date.today() + timedelta(days=385)).isoformat()},
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert proposition.status_code == 201
    body = proposition.json()
    assert body["statut"] == "en_attente"
    assert body["nouveau_contrat_id"] is not None

    signature = client.post(
        f"/api/v1/contrats/{body['nouveau_contrat_id']}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace-du-canvas-en-png"), "image/png")},
        headers=enseignant_headers,
    )
    assert signature.status_code == 200
    assert signature.json()["statut"] == "signe"


def test_lister_postes_mes_candidatures_et_mes_contrats(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.score_par_defaut = 85.0
    candidature = _postuler_et_relire(client, enseignant_headers, poste["id"]).json()

    postes = client.get(
        f"/api/v1/etablissements/{etablissement_avec_classe['etablissement']['id']}/postes", headers=enseignant_headers
    )
    assert postes.status_code == 200
    assert any(p["id"] == poste["id"] for p in postes.json())

    mes_candidatures = client.get("/api/v1/mes-candidatures", headers=enseignant_headers)
    assert mes_candidatures.status_code == 200
    assert any(c["id"] == candidature["id"] for c in mes_candidatures.json())

    client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme", "date_fin": "2027-06-30"},
        headers=etablissement_avec_classe["admin_headers"],
    )
    mes_contrats = client.get("/api/v1/mes-contrats", headers=enseignant_headers)
    assert mes_contrats.status_code == 200
    assert len(mes_contrats.json()) == 1


def test_contestations_en_attente_visibles_par_admin(
    client, fake_llm_client, enseignant_headers, etablissement_avec_classe
):
    poste = _creer_poste(client, etablissement_avec_classe["admin_headers"], etablissement_avec_classe["etablissement"]["id"])
    fake_llm_client.scores_par_type = {"cv": 40.0, "diplome": 90.0}
    candidature = _postuler_et_relire(client, enseignant_headers, poste["id"]).json()
    assert candidature["statut"] == "rejetee"

    client.post(
        f"/api/v1/candidatures/{candidature['id']}/contestation",
        json={"motif": "Le CV a ete mal interprete"},
        headers=enseignant_headers,
    )

    en_attente = client.get(
        f"/api/v1/etablissements/{etablissement_avec_classe['etablissement']['id']}/contestations-en-attente",
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert en_attente.status_code == 200
    assert len(en_attente.json()) == 1
    assert en_attente.json()[0]["candidature_id"] == candidature["id"]
