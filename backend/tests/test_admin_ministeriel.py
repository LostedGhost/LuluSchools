from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def kkiapay_secret(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "kkiapay_secret", "secret-de-test")
    return "secret-de-test"


def _payer_via_webhook(client, transaction_id, secret):
    return client.post(
        "/api/v1/paiements/webhook/kkiapay",
        json={"transactionId": transaction_id, "isPaymentSucces": True, "event": "transaction.success"},
        headers={"x-kkiapay-secret": secret},
    )


def test_modifier_description_etablissement(client, etablissement_avec_classe, admin_ministeriel_headers):
    etablissement_id = etablissement_avec_classe["etablissement"]["id"]
    reponse = client.patch(
        f"/api/v1/etablissements/{etablissement_id}/description",
        json={"description": "Un etablissement pilote du reseau national."},
        headers=admin_ministeriel_headers,
    )
    assert reponse.status_code == 200
    assert reponse.json()["description"] == "Un etablissement pilote du reseau national."
    assert reponse.json()["actif"] is True


def test_action_groupee_suspendre_retire_de_l_annuaire_public(
    client, etablissement_avec_classe, admin_ministeriel_headers
):
    etablissement_id = etablissement_avec_classe["etablissement"]["id"]
    avant = client.get("/api/v1/etablissements/annuaire-public").json()
    assert any(e["id"] == etablissement_id for e in avant["items"])

    suspension = client.post(
        "/api/v1/etablissements/action-groupee",
        json={"ids": [etablissement_id], "action": "suspendre", "motif": "Controle en cours"},
        headers=admin_ministeriel_headers,
    )
    assert suspension.status_code == 200
    assert suspension.json()[0]["actif"] is False

    apres = client.get("/api/v1/etablissements/annuaire-public").json()
    assert all(e["id"] != etablissement_id for e in apres["items"])

    journal = client.get("/api/v1/admin/journal-audit", headers=admin_ministeriel_headers).json()
    assert any(
        e["cible_id"] == etablissement_id and e["action"] == "etablissement.suspendre" for e in journal["items"]
    )

    reactivation = client.post(
        "/api/v1/etablissements/action-groupee",
        json={"ids": [etablissement_id], "action": "reactiver", "motif": "Controle termine"},
        headers=admin_ministeriel_headers,
    )
    assert reactivation.json()[0]["actif"] is True


def test_referentiel_edition_directe_par_a_plus_plus(client, admin_ministeriel_headers):
    referentiel = client.post(
        "/api/v1/referentiels-coefficients",
        json={"niveau": "CE1", "matiere": "Mathematiques", "coefficient": 2},
        headers=admin_ministeriel_headers,
    ).json()

    modification = client.patch(
        f"/api/v1/referentiels-coefficients/{referentiel['id']}",
        json={"coefficient": 3},
        headers=admin_ministeriel_headers,
    )
    assert modification.status_code == 200
    assert modification.json()["coefficient"] == 3


def test_validation_en_lot_de_propositions_referentiel(client, admin_ministeriel_headers, etablissement_avec_classe):
    referentiel = client.post(
        "/api/v1/referentiels-coefficients",
        json={"niveau": "CE1", "matiere": "Francais", "coefficient": 1},
        headers=admin_ministeriel_headers,
    ).json()
    proposition = client.post(
        f"/api/v1/referentiels-coefficients/{referentiel['id']}/proposition",
        json={"coefficient": 2},
        headers=etablissement_avec_classe["admin_headers"],
    ).json()

    lot = client.post(
        "/api/v1/referentiels-coefficients/valider-lot",
        json={"ids": [proposition["id"]]},
        headers=admin_ministeriel_headers,
    )
    assert lot.status_code == 200
    assert lot.json()[0]["statut"] == "valide"


def _offre_acceptee(client, ctx, kkiapay_secret):
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours de soutien", "description": "Aide aux devoirs", "prix": 5000},
        headers=ctx["tuteur_headers"],
    ).json()
    client.post(
        f"/api/v1/micro-jobs/offres/{offre['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{offre['id']}"},
        headers=ctx["tuteur_headers"],
    )
    _payer_via_webhook(client, f"tx-{offre['id']}", kkiapay_secret)
    mission = client.post(f"/api/v1/micro-jobs/offres/{offre['id']}/accepter", headers=ctx["enseignant_headers"]).json()
    return offre, mission


def test_file_de_contestations_micro_job_avec_contexte(
    client, classe_avec_enseignant_et_eleve, kkiapay_secret, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    offre, mission = _offre_acceptee(client, ctx, kkiapay_secret)
    client.post(f"/api/v1/missions-micro-job/{mission['id']}/declarer-fin", headers=ctx["enseignant_headers"])
    contestation = client.post(
        f"/api/v1/missions-micro-job/{mission['id']}/contester",
        json={"motif": "Travail non conforme"},
        headers=ctx["tuteur_headers"],
    ).json()

    file_attente = client.get("/api/v1/contestations-micro-job", headers=admin_ministeriel_headers)
    assert file_attente.status_code == 200
    entree = next(c for c in file_attente.json() if c["id"] == contestation["id"])
    assert entree["offre_titre"] == "Cours de soutien"
    assert entree["prix"] == 5000
    assert entree["prestataire_prenom"]


def test_file_des_reversements_en_attente(
    client, classe_avec_enseignant_et_eleve, kkiapay_secret, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    offre, mission = _offre_acceptee(client, ctx, kkiapay_secret)
    client.post(f"/api/v1/missions-micro-job/{mission['id']}/declarer-fin", headers=ctx["enseignant_headers"])
    client.post(f"/api/v1/missions-micro-job/{mission['id']}/valider", headers=ctx["tuteur_headers"])

    file_attente = client.get("/api/v1/missions-micro-job/a-reverser", headers=admin_ministeriel_headers)
    assert file_attente.status_code == 200
    entree = next(m for m in file_attente.json() if m["id"] == mission["id"])
    assert entree["prix_paye"] == 5000

    client.post(
        f"/api/v1/missions-micro-job/{mission['id']}/reverser-prestataire",
        json={"reference_paiement": "MOMO-REF-1"},
        headers=admin_ministeriel_headers,
    )
    apres = client.get("/api/v1/missions-micro-job/a-reverser", headers=admin_ministeriel_headers).json()
    assert all(m["id"] != mission["id"] for m in apres)


def test_recherche_utilisateurs_et_suspension_de_compte(
    client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    recherche = client.get(
        "/api/v1/admin/utilisateurs", params={"q": "Traore"}, headers=admin_ministeriel_headers
    )
    assert recherche.status_code == 200
    assert recherche.json()["total"] >= 1
    enseignant_id = recherche.json()["items"][0]["id"]

    suspension = client.post(
        f"/api/v1/admin/utilisateurs/{enseignant_id}/suspendre",
        json={"motif": "Signalement en cours d'instruction"},
        headers=admin_ministeriel_headers,
    )
    assert suspension.status_code == 200
    assert suspension.json()["actif"] is False

    bloque = client.get("/api/v1/mes-classes-affectees", headers=ctx["enseignant_headers"])
    assert bloque.status_code == 403
    assert bloque.json()["error"]["code"] == "compte_suspendu"

    reactivation = client.post(
        f"/api/v1/admin/utilisateurs/{enseignant_id}/reactiver",
        json={},
        headers=admin_ministeriel_headers,
    )
    assert reactivation.json()["actif"] is True
    debloque = client.get("/api/v1/mes-classes-affectees", headers=ctx["enseignant_headers"])
    assert debloque.status_code == 200


def test_admin_ministeriel_ne_peut_pas_se_suspendre_lui_meme(client, admin_ministeriel, admin_ministeriel_headers):
    reponse = client.post(
        f"/api/v1/admin/utilisateurs/{admin_ministeriel.id}/suspendre",
        json={"motif": "Test"},
        headers=admin_ministeriel_headers,
    )
    assert reponse.status_code == 409


def test_masquer_cours_le_retire_de_la_vue_eleve_pas_de_l_enseignant(
    client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    cours = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": "Chapitre 1", "chapitre": "Introduction", "format": "texte", "contenu_texte": "Contenu."},
        headers=ctx["enseignant_headers"],
    ).json()

    masquage = client.post(
        f"/api/v1/cours/{cours['id']}/masquer", json={"motif": "Contenu signale"}, headers=admin_ministeriel_headers
    )
    assert masquage.status_code == 200

    vue_eleve = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["eleve_headers"]).json()
    assert all(c["id"] != cours["id"] for c in vue_eleve)
    vue_enseignant = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["enseignant_headers"]).json()
    assert any(c["id"] == cours["id"] for c in vue_enseignant)

    supervision = client.get("/api/v1/admin/cours", params={"masque": True}, headers=admin_ministeriel_headers).json()
    assert any(c["id"] == cours["id"] for c in supervision["items"])

    demasquage = client.post(f"/api/v1/cours/{cours['id']}/demasquer", headers=admin_ministeriel_headers)
    assert demasquage.status_code == 200
    vue_eleve_apres = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["eleve_headers"]).json()
    assert any(c["id"] == cours["id"] for c in vue_eleve_apres)


def _creer_evenement(client, ctx, date_heure=None):
    date_heure = date_heure or (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    return client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/evenements",
        json={
            "titre": "Kermesse",
            "description": "Fete de fin d'annee",
            "lieu": "Cour de l'ecole",
            "date_heure": date_heure,
            "capacite_max": 10,
            "prix_billet": 0,
        },
        headers=ctx["admin_headers"],
    ).json()


def test_supervision_evenements_et_annulation_urgence_journalisee(
    client, etablissement_avec_classe, admin_ministeriel_headers
):
    evenement = _creer_evenement(client, etablissement_avec_classe)

    supervision = client.get("/api/v1/admin/evenements", headers=admin_ministeriel_headers)
    assert supervision.status_code == 200
    assert any(e["id"] == evenement["id"] for e in supervision.json()["items"])

    annulation = client.post(f"/api/v1/evenements/{evenement['id']}/annuler", headers=admin_ministeriel_headers)
    assert annulation.status_code == 200
    assert annulation.json()["statut"] == "annule"

    journal = client.get("/api/v1/admin/journal-audit", headers=admin_ministeriel_headers).json()
    assert any(e["cible_id"] == evenement["id"] and e["action"] == "evenement.annuler_urgence" for e in journal["items"])
