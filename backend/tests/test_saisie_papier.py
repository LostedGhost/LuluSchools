"""Saisie papier : l'administration enregistre, depuis une photo lue par l'IA puis relue par
un humain, les documents papier des personnes sans smartphone."""

import base64
import io
from datetime import datetime, timedelta, timezone

from conftest import periode_courante
from PIL import Image
from test_evaluations import _creer_devoir, _extraire_sub

from app.core.security import decode_token
from app.modules.evaluations.models import Soumission, StatutSoumission
from app.modules.recrutement.models import Contrat, StatutContrat
from app.modules.saisie_papier import router as saisie_router
from app.modules.saisie_papier.models import DocumentPapier
from app.modules.vie_scolaire.models import EntreeVieScolaire


def _photo(nom="feuille.jpg"):
    image = io.BytesIO()
    Image.new("RGB", (60, 40), "white").save(image, format="JPEG")
    return ("fichiers", (nom, image.getvalue(), "image/jpeg"))


def _lire(client, ctx, type_doc, classe=True, fichiers=None):
    return client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/saisie-papier/lire",
        data={"type": type_doc, **({"classe_id": ctx["classe"]["id"]} if classe else {})},
        files=fichiers or [_photo()],
        headers=ctx["admin_headers"],
    )


def _texte_pdf(contenu: bytes) -> str:
    import pymupdf as fitz

    with fitz.open(stream=contenu, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def _enseignant_id(ctx):
    return decode_token(ctx["enseignant_headers"]["Authorization"].split(" ")[1])["sub"]


def test_feuille_de_notes_lue_puis_validee(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    fake_llm_client.lectures_papier["feuille de notes"] = {
        "matiere": "Mathématiques", "titre": "Devoir n°2", "note_sur": 20,
        "lignes": [{"nom": "DOSSOU Aïsha", "note": 14.5, "absent": False, "lisible": True},
                   {"nom": "Personne Inconnue", "note": 3, "absent": False, "lisible": True}],
    }
    contexte = client.get(f"/api/v1/classes/{ctx['classe']['id']}/saisie-papier/contexte", headers=ctx["admin_headers"]).json()
    assert [e["id"] for e in contexte["enseignants"]] == [_enseignant_id(ctx)] and len(contexte["eleves"]) == 1
    lu = _lire(client, ctx, "feuille_notes").json()
    eleve_id = lu["eleves"][0]["eleve_id"]
    assert lu["lignes"][0]["eleve_id"] == eleve_id and lu["lignes"][0]["confiance"] == "sur"
    assert lu["lignes"][1]["eleve_id"] is None and lu["lignes"][1]["confiance"] == "non_trouve"

    payload = {
        "classe_id": ctx["classe"]["id"], "enseignant_id": _enseignant_id(ctx), "matiere": "Mathématiques",
        "titre": "Devoir n°2", "date_evaluation": (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat(),
        "note_sur": 20, "lignes": [{"eleve_id": eleve_id, "note": 24}],
    }
    url = f"/api/v1/saisie-papier/{lu['document_id']}/notes"
    assert client.post(url, json=payload, headers=ctx["admin_headers"]).json()["error"]["code"] == "note_hors_bareme"
    payload["lignes"][0]["note"] = 14.5
    ok = client.post(url, json=payload, headers=ctx["admin_headers"])
    assert ok.status_code == 200 and ok.json()["nombre"] == 1
    assert client.post(url, json=payload, headers=ctx["admin_headers"]).status_code == 409

    bulletin = client.get(
        f"/api/v1/eleves/{_extraire_sub(ctx)}/bulletins",
        params={"classe_id": ctx["classe"]["id"], "periode": periode_courante(client, ctx["classe"]["id"], ctx["admin_headers"])},
        headers=ctx["admin_headers"],
    ).json()
    assert bulletin["moyenne_generale"] == 72.5  # 14,5 / 20


def test_feuille_d_appel_saisie_a_la_main_si_l_ia_echoue(client, classe_avec_enseignant_et_eleve, fake_llm_client, db_session):
    ctx = classe_avec_enseignant_et_eleve
    fake_llm_client.echec_lecture_papier = True
    lu = _lire(client, ctx, "feuille_appel").json()
    assert lu["lecture"] is None and lu["erreur_lecture"] and len(lu["eleves"]) == 1
    eleve_id = lu["eleves"][0]["eleve_id"]
    reponse = client.post(
        f"/api/v1/saisie-papier/{lu['document_id']}/appel",
        json={"classe_id": ctx["classe"]["id"], "date": datetime.now(timezone.utc).date().isoformat(),
              "lignes": [{"eleve_id": eleve_id, "statut": "absent", "commentaire": "Malade"}]},
        headers=ctx["admin_headers"],
    )
    assert reponse.json()["nombre"] == 1
    entree = db_session.query(EntreeVieScolaire).filter(EntreeVieScolaire.eleve_id == eleve_id).one()
    assert "feuille d'appel papier" in entree.description and "Malade" in entree.description


def test_cours_ecrit_publie_au_nom_de_l_enseignant(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    fake_llm_client.lectures_papier["cours écrit"] = {"titre": "Les fractions", "chapitre": "Chapitre 3", "contenu": "## Définition\nUne fraction..."}
    lu = _lire(client, ctx, "cours", classe=False).json()
    assert lu["lecture"]["titre"] == "Les fractions"
    reponse = client.post(
        f"/api/v1/saisie-papier/{lu['document_id']}/cours",
        json={"classe_id": ctx["classe"]["id"], "enseignant_id": _enseignant_id(ctx), "titre": "Les fractions",
              "chapitre": "Chapitre 3", "contenu": lu["lecture"]["contenu"]},
        headers=ctx["admin_headers"],
    )
    assert reponse.status_code == 200
    cours = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["eleve_headers"]).json()
    assert any(c["titre"] == "Les fractions" for c in cours)


def test_inscription_au_guichet_avec_fiche_d_identifiants(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    fake_llm_client.lectures_papier["fiche d'inscription"] = {
        "eleve_nom": "Houngbo", "eleve_prenom": "Mawuli", "date_naissance": "2014-02-03", "classe_demandee": ctx["classe"]["niveau"],
        "tuteur_nom": "Houngbo Pascal", "tuteur_telephone": "+229 01 97 00 00 00", "signature_parent": True,
    }
    lu = _lire(client, ctx, "fiche_inscription", classe=False).json()
    assert lu["classe_proposee_id"] == ctx["classe"]["id"]
    payload = {"classe_id": ctx["classe"]["id"], "nom": "Houngbo", "prenom": "Mawuli", "date_naissance": "2014-02-03",
               "tuteur_nom": "Houngbo Pascal", "consentement_signe": False}
    url = f"/api/v1/saisie-papier/{lu['document_id']}/inscription"
    assert client.post(url, json=payload, headers=ctx["admin_headers"]).json()["error"]["code"] == "consentement_manquant"
    payload["consentement_signe"] = True
    # Classe de capacite 1 deja occupee : l'inscription reste en attente, avec l'explication.
    refus = client.post(url, json=payload, headers=ctx["admin_headers"])
    assert refus.status_code == 409 and refus.json()["error"]["code"] == "classe_complete"


def test_inscription_au_guichet_validee(client, etablissement_avec_classe, fake_llm_client):
    ctx = etablissement_avec_classe  # classe vide, capacite 1
    lu = _lire(client, ctx, "fiche_inscription", classe=False).json()
    reponse = client.post(
        f"/api/v1/saisie-papier/{lu['document_id']}/inscription",
        json={"classe_id": ctx["classe"]["id"], "nom": "Houngbo", "prenom": "Mawuli", "date_naissance": "2005-02-03",
              "tuteur_nom": "Houngbo Pascal"},
        headers=ctx["admin_headers"],
    ).json()
    assert reponse["matricule"] and reponse["mot_de_passe_provisoire"]
    assert base64.b64decode(reponse["fiche_identifiants_pdf"]).startswith(b"%PDF")
    connexion = client.post("/api/v1/auth/login", json={"identifiant": reponse["matricule"], "mot_de_passe": reponse["mot_de_passe_provisoire"]})
    assert connexion.status_code == 200


def test_copies_papier_attribuees_puis_corrigees(client, classe_avec_enseignant_et_eleve, fake_llm_client, db_session, monkeypatch):
    ctx = classe_avec_enseignant_et_eleve
    devoir = _creer_devoir(client, ctx, datetime.now(timezone.utc) - timedelta(days=1))  # echeance passee
    fake_llm_client.noms_copies = ["Aisha Dossou"]
    monkeypatch.setattr(saisie_router, "telecharger_copie", lambda files_client, file_id: _photo()[1][1])
    lu = client.post(f"/api/v1/devoirs/{devoir['id']}/copies-papier/lire", files=[_photo("copie1.jpg")],
                     headers=ctx["enseignant_headers"]).json()
    copie = lu["copies"][0]
    assert copie["eleve_id"] == lu["eleves"][0]["eleve_id"] and copie["confiance"] == "sur"
    reponse = client.post(
        f"/api/v1/devoirs/{devoir['id']}/copies-papier/enregistrer",
        json={"affectations": [{"document_id": copie["document_id"], "eleve_id": copie["eleve_id"]}]},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.json()["nombre"] == 1
    soumission = db_session.query(Soumission).filter(Soumission.devoir_id == devoir["id"]).one()
    db_session.refresh(soumission)
    assert soumission.statut == StatutSoumission.CORRIGEE and soumission.note == 20


def test_contrat_signe_sur_papier(client, classe_avec_enseignant_et_eleve, db_session):
    ctx = classe_avec_enseignant_et_eleve
    signe = db_session.query(Contrat).first()
    contrat = Contrat(candidature_id=signe.candidature_id, enseignant_id=signe.enseignant_id, etablissement_id=signe.etablissement_id,
                      syllabus="Reconduction", date_fin=signe.date_fin, statut=StatutContrat.EN_ATTENTE_SIGNATURE)
    db_session.add(contrat)
    db_session.commit()
    url = f"/api/v1/contrats/{contrat.id}/signature-papier"
    assert client.post(url, files=[_photo("p1.jpg")], headers=ctx["enseignant_headers"]).status_code == 403
    assert client.post(url, files=[_photo("p1.jpg"), _photo("p2.jpg")], headers=ctx["admin_headers"]).status_code == 200
    db_session.refresh(contrat)
    assert contrat.statut == StatutContrat.SIGNE and contrat.signature_horodatage
    assert len(db_session.query(DocumentPapier).filter(DocumentPapier.objet_id == contrat.id).one().fichiers) == 2
    texte = _texte_pdf(client.get(f"/api/v1/contrats/{contrat.id}/pdf", headers=ctx["admin_headers"]).content)
    assert "Contrat signé à la main sur papier" in texte


def test_consentement_parental_sur_papier(client, etablissement_avec_classe, tuteur_headers):
    ctx = etablissement_avec_classe
    inscription = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Hounkpe", "prenom": "Fifame", "date_naissance": "2016-03-01", "classe_id": ctx["classe"]["id"]},
        headers=tuteur_headers,
    ).json()
    assert inscription["statut"] == "en_attente_consentement_parental"
    attente = client.get(f"/api/v1/etablissements/{ctx['etablissement']['id']}/saisie-papier/consentements-en-attente",
                         headers=ctx["admin_headers"]).json()
    assert [a["inscription_id"] for a in attente] == [inscription["id"]]
    reponse = client.post(f"/api/v1/inscriptions/{inscription['id']}/consentement-papier",
                          files=[_photo("consentement.jpg")], headers=ctx["admin_headers"])
    assert reponse.status_code == 200
    apres = client.get(f"/api/v1/inscriptions/{inscription['id']}", headers=ctx["admin_headers"]).json()
    assert apres["statut"] == "soumise" and apres["consentement_parental_horodatage"]
    historique = client.get(f"/api/v1/etablissements/{ctx['etablissement']['id']}/saisie-papier/historique", headers=ctx["admin_headers"]).json()
    assert historique[0]["type"] == "consentement" and historique[0]["statut"] == "enregistre"


def test_reserve_a_l_administration(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    refus = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/saisie-papier/lire",
        data={"type": "feuille_notes", "classe_id": ctx["classe"]["id"]}, files=[_photo()], headers=ctx["eleve_headers"],
    )
    assert refus.status_code == 403
