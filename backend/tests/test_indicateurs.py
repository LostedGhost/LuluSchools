"""Lot 7.6 : territoire des etablissements, sexe des eleves et indicateurs de pilotage."""

from datetime import date

from app.modules.etablissements.models import annee_academique_courante
from app.modules.evaluations.models import Bulletin
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription


def _creer_etablissement(client, headers, **extra):
    return client.post(
        "/api/v1/etablissements",
        json={
            "nom": "CEG Test Territoire", "type": "ES", "statut": "public",
            "admin": {"nom": "Admin", "prenom": "Territoire", "email": "admin.territoire@example.com"},
            "latitude": 6.4, "longitude": 2.4, **extra,
        },
        headers=headers,
    )


def test_territoire_liste_fermee(client, admin_ministeriel_headers):
    territoires = client.get("/api/v1/etablissements/territoires").json()
    assert len(territoires) == 12 and sum(len(c) for c in territoires.values()) == 77
    assert "Cotonou" in territoires["Littoral"]

    mauvaise_commune = _creer_etablissement(client, admin_ministeriel_headers, departement="Littoral", commune="Parakou")
    assert mauvaise_commune.status_code == 422
    ok = _creer_etablissement(client, admin_ministeriel_headers, departement="Borgou", commune="Parakou")
    assert ok.status_code == 201
    assert ok.json()["departement"] == "Borgou" and ok.json()["commune"] == "Parakou"

    maj = client.patch(
        f"/api/v1/etablissements/{ok.json()['id']}/territoire",
        json={"departement": "Donga", "commune": "Djougou"},
        headers=admin_ministeriel_headers,
    )
    assert maj.status_code == 200 and maj.json()["commune"] == "Djougou"


def test_sexe_facultatif_a_l_inscription(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    payload = {"nom": "Houngbo", "prenom": "Rita", "date_naissance": "2009-03-01", "classe_id": ctx["classe"]["id"], "sexe": "F"}
    assert client.post("/api/v1/inscriptions", json=payload, headers=ctx["tuteur_headers"]).status_code == 201
    payload.update(prenom="Zoe", sexe="X")
    assert client.post("/api/v1/inscriptions", json=payload, headers=ctx["tuteur_headers"]).status_code == 422


def _peupler(db_session, classe_id, filles, garcons, moyenne=60.0):
    for i in range(filles + garcons):
        eleve = Eleve(nom="Test", prenom=f"E{i}", date_naissance=date(2012, 1, 1), sexe="F" if i < filles else "M")
        db_session.add(eleve)
        db_session.flush()
        db_session.add(Inscription(eleve_id=eleve.id, classe_id=classe_id, statut=StatutInscription.VALIDEE))
        db_session.add(Bulletin(eleve_id=eleve.id, classe_id=classe_id, periode="trimestre1", moyenne_generale=moyenne))
    db_session.commit()


def test_indicateurs_nationaux_calcules_et_petits_effectifs_masques(
    client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers, db_session
):
    ctx = classe_avec_enseignant_et_eleve
    # 6 filles, 3 garcons (+ l'eleve du socle, sexe non renseigne)
    _peupler(db_session, ctx["classe"]["id"], filles=6, garcons=3)
    donnees = client.get("/api/v1/admin/indicateurs", headers=admin_ministeriel_headers).json()
    assert donnees["perimetre"] == "National"
    assert donnees["annee_academique"] == annee_academique_courante()
    assert donnees["eleves"]["total"] == 10
    assert donnees["eleves"]["filles"] == 6
    assert donnees["eleves"]["garcons"] is None  # 3 < 5 : masque
    assert donnees["eleves"]["indice_parite"] is None
    assert donnees["reussite"]["taux_reussite"] == 100.0
    assert donnees["reussite"]["taux_reussite_garcons"] is None
    assert donnees["enseignants"]["sous_contrat"] == 1
    assert len(donnees["par_departement"]) == 12
    assert "inclusion" in donnees and "comptes_mode_ecoute" in donnees["inclusion"]


def test_admin_etablissement_limite_a_son_etablissement(client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers):
    ctx = classe_avec_enseignant_et_eleve
    # Un autre etablissement, que l'A+ ne doit jamais voir, meme en le demandant.
    autre = _creer_etablissement(client, admin_ministeriel_headers, departement="Zou", commune="Abomey").json()
    donnees = client.get(
        f"/api/v1/admin/indicateurs?etablissement_id={autre['id']}", headers=ctx["admin_headers"]
    ).json()
    assert donnees["perimetre"] == "Établissement"
    assert donnees["etablissements"]["total"] == 1
    assert "par_departement" not in donnees
    assert client.get("/api/v1/admin/indicateurs", headers=ctx["enseignant_headers"]).status_code == 403


def test_export_csv(client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers):
    reponse = client.get("/api/v1/admin/indicateurs.csv", headers=admin_ministeriel_headers)
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/csv")
    texte = reponse.text.lstrip("﻿")
    assert texte.startswith("indicateur;valeur")
    assert "eleves.total;" in texte
    assert "departement;etablissements;eleves" in texte
    assert client.get("/api/v1/admin/indicateurs?departement=Inconnu", headers=admin_ministeriel_headers).status_code == 422
