"""Lot 7.8 : EFTP, offres de stage, competences metier et bourses scientifiques."""

from datetime import date, timedelta

import pytest

OFFRE = {
    "entreprise": "SONEB", "intitule": "Stage technicien réseau d'eau", "description": "Maintenance des réseaux de distribution.",
    "lieu": "Cotonou", "duree_semaines": 8, "date_limite": str(date.today() + timedelta(days=20)), "contact": "rh@soneb.example",
}


def _offre(client, ctx, **extra):
    reponse = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/stages", json={**OFFRE, **extra}, headers=ctx["admin_headers"]
    )
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def test_stage_publie_candidature_et_decision(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    offre = _offre(client, ctx)
    visibles = client.get("/api/v1/stages", headers=ctx["eleve_headers"]).json()
    assert [o["id"] for o in visibles] == [offre["id"]] and visibles[0]["ma_candidature"] is None

    url = f"/api/v1/stages/{offre['id']}/candidatures"
    candidature = client.post(url, json={"message": "Je suis motivée par les métiers de l'eau."}, headers=ctx["eleve_headers"])
    assert candidature.status_code == 201
    assert client.post(url, json={"message": "Deuxième envoi identique."}, headers=ctx["eleve_headers"]).status_code == 409
    assert client.get("/api/v1/stages", headers=ctx["eleve_headers"]).json()[0]["ma_candidature"] == "envoyee"

    liste = client.get(url, headers=ctx["admin_headers"]).json()
    assert liste[0]["eleve_prenom"] and liste[0]["statut"] == "envoyee"
    decision = client.post(
        f"/api/v1/candidatures-stage/{liste[0]['id']}/decision", json={"statut": "retenue"}, headers=ctx["admin_headers"]
    )
    assert decision.json()["statut"] == "retenue"

    client.post(f"/api/v1/stages/{offre['id']}/cloturer", headers=ctx["admin_headers"])
    assert client.get("/api/v1/stages", headers=ctx["eleve_headers"]).json() == []


def test_offre_date_passee_et_autre_etablissement_refuses(client, classe_avec_enseignant_et_eleve, etudiant_headers):
    ctx = classe_avec_enseignant_et_eleve
    passee = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/stages",
        json={**OFFRE, "date_limite": str(date.today() - timedelta(days=1))},
        headers=ctx["admin_headers"],
    )
    assert passee.status_code == 422
    offre = _offre(client, ctx)
    refus = client.post(
        f"/api/v1/stages/{offre['id']}/candidatures", json={"message": "Je viens d'une autre université."}, headers=etudiant_headers
    )
    assert refus.status_code == 403


def test_competence_metier_validee_par_un_enseignant_de_la_classe(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    url = f"/api/v1/eleves/{eleve_id}/competences-metier"
    ok = client.post(url, json={"intitule": "Souder à l'arc", "niveau": "confirme"}, headers=ctx["enseignant_headers"])
    assert ok.status_code == 201
    assert client.post(url, json={"intitule": "Auto-validation", "niveau": "maitrise"}, headers=ctx["eleve_headers"]).status_code == 403
    passeport = client.get("/api/v1/eleves/me/passeport", headers=ctx["eleve_headers"]).json()
    assert passeport["competences_metier"] == [{"intitule": "Souder à l'arc", "niveau": "confirmé"}]
    assert client.get(url, headers=ctx["tuteur_headers"]).json()[0]["intitule"] == "Souder à l'arc"


@pytest.fixture()
def notes_simulees(monkeypatch):
    from app.modules.insertion import service

    notes: list[tuple[str, float, float]] = []
    monkeypatch.setattr(service, "notes_de_la_periode", lambda *a: notes)
    return notes


def test_bourse_scientifique_eligibilite_et_controle_a_la_demande(client, classe_avec_enseignant_et_eleve, notes_simulees):
    ctx = classe_avec_enseignant_et_eleve
    type_acte = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-actes",
        json={"nom": "Bourse filières scientifiques", "pieces_requises": "Aucune", "critere_automatique": "bourse_scientifique"},
        headers=ctx["admin_headers"],
    ).json()
    assert type_acte["critere_automatique"] == "bourse_scientifique"

    url = "/api/v1/bourses/eligibilite-scientifique"
    assert client.get(url, headers=ctx["eleve_headers"]).json()["eligible"] is False  # aucune note

    notes_simulees[:] = [("Mathématiques", 50.0, 4.0), ("Français", 90.0, 2.0)]  # 10/20 en sciences
    refus = client.post("/api/v1/demandes-actes", json={"type_acte_id": type_acte["id"]}, headers=ctx["eleve_headers"])
    assert refus.status_code == 422 and "12/20" in refus.json()["error"]["message"]

    notes_simulees[:] = [("Mathématiques", 70.0, 4.0), ("Physique-Chimie", 60.0, 2.0)]  # 13,33/20
    eligibilite = client.get(url, headers=ctx["eleve_headers"]).json()
    assert eligibilite["eligible"] is True and eligibilite["matieres"] == ["Mathématiques", "Physique-Chimie"]
    accepte = client.post("/api/v1/demandes-actes", json={"type_acte_id": type_acte["id"]}, headers=ctx["eleve_headers"])
    assert accepte.status_code == 201


def test_classe_eftp_comptee_dans_les_indicateurs(client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers):
    ctx = classe_avec_enseignant_et_eleve
    classe = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/classes",
        json={"niveau": "2nde", "filiere": "F4", "capacite": 30, "politique_depassement": "ordre_arrivee", "enseignement": "technique"},
        headers=ctx["admin_headers"],
    )
    assert classe.status_code == 201 and classe.json()["enseignement"] == "technique"
    donnees = client.get("/api/v1/admin/indicateurs", headers=admin_ministeriel_headers).json()
    assert "eftp" in donnees and donnees["eftp"]["eleves"] == 0
