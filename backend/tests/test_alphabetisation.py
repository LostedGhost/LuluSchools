"""Lot 7.7 : centres d'alphabetisation, inscription des adultes, cours et quiz oral."""

import pytest

from app.modules.pedagogie.models import Cours, FormatCours, QuestionQuiz, Quiz
from tests.conftest import token_pour


@pytest.fixture()
def centre(client, admin_ministeriel_headers, fake_email_client, db_session):
    """Un centre d'alphabetisation, une classe de 2 places et un cours avec quiz."""
    etab = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Centre d'alphabétisation de Bohicon", "type": "CA", "statut": "public",
            "admin": {"nom": "Admin", "prenom": "Centre", "email": "admin.centre@example.com"},
            "latitude": 7.17, "longitude": 2.07, "departement": "Zou", "commune": "Bohicon",
        },
        headers=admin_ministeriel_headers,
    )
    assert etab.status_code == 201, etab.text
    etab = etab.json()
    mdp = next(m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "admin.centre@example.com")
    login = client.post("/api/v1/auth/login", json={"identifiant": "admin.centre@example.com", "mot_de_passe": mdp}).json()
    admin = {"Authorization": f"Bearer {login['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mdp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=admin,
    )
    classe = client.post(
        f"/api/v1/etablissements/{etab['id']}/classes",
        json={"niveau": "Alphabétisation initiale", "capacite": 2, "politique_depassement": "ordre_arrivee"},
        headers=admin,
    )
    assert classe.status_code == 201, classe.text
    classe = classe.json()
    # Cours et quiz inseres directement : l'affectation d'un enseignant est deja couverte ailleurs.
    from app.modules.identite.models import Utilisateur

    auteur = db_session.query(Utilisateur).filter(Utilisateur.login_id == "admin.centre@example.com").one()
    cours = Cours(
        classe_id=classe["id"], enseignant_id=auteur.id, titre="Les voyelles", chapitre="Lecture",
        format=FormatCours.TEXTE, contenu_texte="A, E, I, O, U sont les voyelles.",
    )
    db_session.add(cours)
    db_session.flush()
    quiz = Quiz(cours_id=cours.id, seuil_reussite=50)
    db_session.add(quiz)
    db_session.flush()
    db_session.add(QuestionQuiz(quiz_id=quiz.id, ordre=1, enonce="Laquelle est une voyelle ?", choix=["B", "A", "T"], reponse_correcte_index=1))
    db_session.commit()
    return {"etablissement": etab, "classe": classe, "admin_headers": admin, "cours_id": cours.id, "quiz_id": quiz.id}


def _tuteur(db_session, login):
    from tests.conftest import creer_utilisateur_direct
    from app.modules.identite.models import RoleUtilisateur, Tuteur

    u = creer_utilisateur_direct(db_session, role=RoleUtilisateur.TUTEUR, login_id=login, prenom="Adjoa")
    db_session.add(Tuteur(utilisateur_id=u.id))
    db_session.commit()
    return {"Authorization": f"Bearer {token_pour(u)}"}


def test_adulte_s_inscrit_lit_le_cours_et_s_entraine(client, centre, db_session):
    tuteur = _tuteur(db_session, "adjoa.apprenante@example.com")
    classes = client.get("/api/v1/alphabetisation/classes", headers=tuteur).json()
    assert [c["centre_nom"] for c in classes] == ["Centre d'alphabétisation de Bohicon"]
    assert classes[0]["places_restantes"] == 2 and classes[0]["inscrit"] is False

    # Avant l'inscription, aucun acces aux cours du centre.
    assert client.get(f"/api/v1/classes/{centre['classe']['id']}/cours", headers=tuteur).status_code == 403

    inscription = client.post("/api/v1/alphabetisation/inscriptions", json={"classe_id": centre["classe"]["id"]}, headers=tuteur)
    assert inscription.status_code == 201 and inscription.json()["places_restantes"] == 1
    doublon = client.post("/api/v1/alphabetisation/inscriptions", json={"classe_id": centre["classe"]["id"]}, headers=tuteur)
    assert doublon.status_code == 409

    cours = client.get(f"/api/v1/classes/{centre['classe']['id']}/cours", headers=tuteur).json()
    assert cours[0]["titre"] == "Les voyelles"
    quiz = client.get(f"/api/v1/quiz/{centre['quiz_id']}", headers=tuteur)
    assert quiz.status_code == 200
    essai = client.post(f"/api/v1/quiz/{centre['quiz_id']}/essai", json={"reponses": [0]}, headers=tuteur).json()
    assert essai["reussie"] is False and essai["bonnes_reponses"] == [1]
    assert client.post(f"/api/v1/quiz/{centre['quiz_id']}/essai", json={"reponses": [1]}, headers=tuteur).json()["reussie"]

    apprenants = client.get(
        f"/api/v1/etablissements/{centre['etablissement']['id']}/apprenants-adultes", headers=centre["admin_headers"]
    ).json()
    assert [a["prenom"] for a in apprenants] == ["Adjoa"]


def test_classe_complete_et_aucun_enfant_inscrit_en_centre(client, centre, db_session, classe_avec_enseignant_et_eleve):
    for i in range(2):
        tuteur = _tuteur(db_session, f"adulte{i}@example.com")
        assert client.post("/api/v1/alphabetisation/inscriptions", json={"classe_id": centre["classe"]["id"]}, headers=tuteur).status_code == 201
    complet = client.post(
        "/api/v1/alphabetisation/inscriptions",
        json={"classe_id": centre["classe"]["id"]},
        headers=_tuteur(db_session, "adulte9@example.com"),
    )
    assert complet.status_code == 409 and complet.json()["error"]["code"] == "classe_complete"

    enfant = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Test", "prenom": "Enfant", "date_naissance": "2015-01-01", "classe_id": centre["classe"]["id"]},
        headers=classe_avec_enseignant_et_eleve["tuteur_headers"],
    )
    assert enfant.status_code == 409 and enfant.json()["error"]["code"] == "centre_alphabetisation"


def test_indicateur_apprenants_adultes(client, centre, db_session, admin_ministeriel_headers):
    tuteur = _tuteur(db_session, "adjoa2@example.com")
    client.post("/api/v1/alphabetisation/inscriptions", json={"classe_id": centre["classe"]["id"]}, headers=tuteur)
    donnees = client.get("/api/v1/admin/indicateurs", headers=admin_ministeriel_headers).json()
    assert donnees["inclusion"]["apprenants_alphabetisation"] == 1
    assert donnees["etablissements"]["par_type"]["CA"] == 1
