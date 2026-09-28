"""Documents officiels generes par la plateforme : contrat d'enseignement, bulletin par
periode et certificat de reussite (livre automatiquement apres une decision favorable)."""

from datetime import datetime, timedelta, timezone

import pymupdf as fitz
from conftest import periode_courante
from test_evaluations import _creer_devoir, _extraire_sub

from app.modules.recrutement import contrat_pdf


def _texte(contenu: bytes) -> str:
    assert contenu.startswith(b"%PDF")
    with fitz.open(stream=contenu, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def _png() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=60, height=20)
    page.draw_line((5, 15), (55, 5), width=2)
    image = page.get_pixmap().tobytes("png")
    doc.close()
    return image


def test_contrat_signe_en_pdf(client, classe_avec_enseignant_et_eleve, monkeypatch):
    ctx = classe_avec_enseignant_et_eleve
    monkeypatch.setattr(contrat_pdf, "_image_signature", lambda files_client, file_id: _png())
    contrat = client.get("/api/v1/mes-contrats", headers=ctx["enseignant_headers"]).json()[0]

    reponse = client.get(f"/api/v1/contrats/{contrat['id']}/pdf", headers=ctx["enseignant_headers"])
    assert reponse.status_code == 200 and reponse.headers["content-type"] == "application/pdf"
    texte = _texte(reponse.content)
    assert "CONTRAT D'ENSEIGNEMENT" in texte and "Signé électroniquement le" in texte and "SHA-256" in texte
    assert client.get(f"/api/v1/contrats/{contrat['id']}/pdf", headers=ctx["admin_headers"]).status_code == 200
    assert client.get(f"/api/v1/contrats/{contrat['id']}/pdf", headers=ctx["eleve_headers"]).status_code == 403


def test_bulletin_de_la_periode_en_pdf(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    _creer_devoir(client, ctx, datetime.now(timezone.utc) - timedelta(days=2), matiere="Mathématiques")
    periode = periode_courante(client, ctx["classe"]["id"], ctx["eleve_headers"])
    reponse = client.get(
        f"/api/v1/eleves/{_extraire_sub(ctx)}/bulletins/pdf",
        params={"classe_id": ctx["classe"]["id"], "periode": periode},
        headers=ctx["eleve_headers"],
    )
    assert reponse.status_code == 200
    texte = _texte(reponse.content)
    assert "BULLETIN DE NOTES" in texte and "Mathématiques" in texte
    assert "Moyenne générale pondérée : 0.0 / 100" in texte  # devoir non rendu apres l'echeance
    assert "en attente de délibération" in texte


def _capturer_uploads(fake_files_client, monkeypatch) -> dict:
    contenus = {}
    upload = fake_files_client.upload

    def capturer(content, filename, content_type):
        contenus[filename] = content
        return upload(content, filename, content_type)

    monkeypatch.setattr(fake_files_client, "upload", capturer)
    return contenus


def test_attestation_et_releve_complets(client, classe_avec_enseignant_et_eleve, fake_files_client, monkeypatch):
    ctx = classe_avec_enseignant_et_eleve
    contenus = _capturer_uploads(fake_files_client, monkeypatch)
    for nom, modele in (("Attestation de scolarité", "attestation_scolarite"), ("Relevé de notes", "releve_notes")):
        type_acte = client.post(
            f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-actes",
            json={"nom": nom, "prix": 0, "pieces_requises": "Aucune", "modele_document": modele},
            headers=ctx["admin_headers"],
        ).json()
        client.post("/api/v1/demandes-actes", json={"type_acte_id": type_acte["id"]}, headers=ctx["eleve_headers"])
    attestation = _texte(contenus["attestation_scolarite.pdf"])
    assert "ATTESTATION DE SCOLARITÉ" in attestation and "régulièrement inscrit(e)" in attestation
    assert "RELEVÉ DE NOTES" in _texte(contenus["releve_notes.pdf"])


def test_certificat_de_reussite_livre_apres_decision_favorable(client, classe_avec_enseignant_et_eleve, fake_files_client, monkeypatch):
    ctx = classe_avec_enseignant_et_eleve
    contenus = _capturer_uploads(fake_files_client, monkeypatch)
    type_acte = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-actes",
        json={"nom": "Certificat de réussite", "prix": 0, "pieces_requises": "Aucune", "modele_document": "certificat_reussite"},
        headers=ctx["admin_headers"],
    ).json()
    client.post("/api/v1/demandes-actes", json={"type_acte_id": type_acte["id"]}, headers=ctx["eleve_headers"])
    # Aucune deliberation : jamais de certificat automatique, la demande attend.
    assert client.get("/api/v1/mes-demandes-actes", headers=ctx["eleve_headers"]).json()[0]["statut"] == "en_traitement"
    a_traiter = client.get("/api/v1/administration/a-traiter", headers=ctx["admin_headers"]).json()
    acte = next(e for s in a_traiter if s["cle"] == "actes" for e in s["elements"])
    assert acte["groupe"] is None and "conseil de classe" in acte["detail"]

    _creer_devoir(client, ctx, datetime.now(timezone.utc) - timedelta(days=2))
    bulletin = client.get(
        f"/api/v1/eleves/{_extraire_sub(ctx)}/bulletins",
        params={"classe_id": ctx["classe"]["id"], "periode": periode_courante(client, ctx["classe"]["id"], ctx["admin_headers"])},
        headers=ctx["admin_headers"],
    ).json()
    client.post(f"/api/v1/bulletins/{bulletin['id']}/valider-passage", json={"decision": "admis"}, headers=ctx["enseignant_headers"])

    livree = client.get("/api/v1/mes-demandes-actes", headers=ctx["eleve_headers"]).json()[0]
    assert livree["statut"] == "acceptee" and livree["document_final_lulufiles_id"]
    certificat = _texte(contenus["certificat_reussite.pdf"])
    assert "CERTIFICAT DE RÉUSSITE" in certificat and "Admis(e) en classe supérieure" in certificat
