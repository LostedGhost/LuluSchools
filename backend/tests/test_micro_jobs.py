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


def _offre_acceptee(client, ctx, kkiapay_secret):
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours de soutien", "description": "Aide aux devoirs de maths", "prix": 5000},
        headers=ctx["enseignant_headers"],
    ).json()
    mission = client.post(f"/api/v1/micro-jobs/offres/{offre['id']}/accepter", headers=ctx["tuteur_headers"]).json()
    client.post(
        f"/api/v1/missions-micro-job/{mission['id']}/paiement/amorcer",
        json={"transaction_id": f"tx-{mission['id']}"},
        headers=ctx["tuteur_headers"],
    )
    _payer_via_webhook(client, f"tx-{mission['id']}", kkiapay_secret)
    return offre, mission


def test_parcours_complet_mission_validee_et_reversee(
    client, classe_avec_enseignant_et_eleve, kkiapay_secret, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    offre, mission = _offre_acceptee(client, ctx, kkiapay_secret)

    fin = client.post(f"/api/v1/missions-micro-job/{mission['id']}/declarer-fin", headers=ctx["enseignant_headers"])
    assert fin.status_code == 200
    assert fin.json()["statut"] == "terminee_declaree"

    validation = client.post(f"/api/v1/missions-micro-job/{mission['id']}/valider", headers=ctx["tuteur_headers"])
    assert validation.status_code == 200
    assert validation.json()["statut"] == "validee"

    reversement = client.post(
        f"/api/v1/missions-micro-job/{mission['id']}/reverser-prestataire",
        json={"reference_paiement": "MOMO-REF-123"},
        headers=admin_ministeriel_headers,
    )
    assert reversement.status_code == 200
    assert reversement.json()["statut"] == "payee"

    historique_prestataire = client.get("/api/v1/mes-missions-micro-job", headers=ctx["enseignant_headers"])
    assert len(historique_prestataire.json()) == 1
    historique_client = client.get("/api/v1/mes-missions-micro-job", headers=ctx["tuteur_headers"])
    assert len(historique_client.json()) == 1


def test_declarer_fin_refuse_avant_paiement_confirme(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Reparation", "description": "Petit bricolage", "prix": 2000},
        headers=ctx["enseignant_headers"],
    ).json()
    mission = client.post(f"/api/v1/micro-jobs/offres/{offre['id']}/accepter", headers=ctx["tuteur_headers"]).json()

    refus = client.post(f"/api/v1/missions-micro-job/{mission['id']}/declarer-fin", headers=ctx["enseignant_headers"])
    assert refus.status_code == 409
    assert refus.json()["error"]["code"] == "paiement_non_confirme"


def test_eleve_exclu_du_dispositif(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    refus = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours", "description": "Test", "prix": 1000},
        headers=ctx["eleve_headers"],
    )
    assert refus.status_code == 403


def test_impossible_d_accepter_sa_propre_offre(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    offre = client.post(
        "/api/v1/micro-jobs/offres",
        json={"titre": "Cours", "description": "Test", "prix": 1000},
        headers=ctx["enseignant_headers"],
    ).json()
    refus = client.post(f"/api/v1/micro-jobs/offres/{offre['id']}/accepter", headers=ctx["enseignant_headers"])
    assert refus.status_code == 409


def test_contestation_rejetee_exige_un_motif_et_valide_la_mission(
    client, classe_avec_enseignant_et_eleve, kkiapay_secret, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    offre, mission = _offre_acceptee(client, ctx, kkiapay_secret)
    client.post(f"/api/v1/missions-micro-job/{mission['id']}/declarer-fin", headers=ctx["enseignant_headers"])

    contestation = client.post(
        f"/api/v1/missions-micro-job/{mission['id']}/contester",
        json={"motif": "Travail non conforme"},
        headers=ctx["tuteur_headers"],
    )
    assert contestation.status_code == 201

    sans_motif = client.post(
        f"/api/v1/contestations-micro-job/{contestation.json()['id']}/decision",
        json={"decision": "rejetee"},
        headers=admin_ministeriel_headers,
    )
    assert sans_motif.status_code == 422

    decision = client.post(
        f"/api/v1/contestations-micro-job/{contestation.json()['id']}/decision",
        json={"decision": "rejetee", "decision_motif": "Preuve insuffisante"},
        headers=admin_ministeriel_headers,
    )
    assert decision.status_code == 200
    assert decision.json()["statut"] == "rejetee"

    mission_a_jour = client.get("/api/v1/mes-missions-micro-job", headers=ctx["tuteur_headers"]).json()[0]
    assert mission_a_jour["statut"] == "validee"


def test_contestation_acceptee_rembourse_le_client(
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

    decision = client.post(
        f"/api/v1/contestations-micro-job/{contestation['id']}/decision",
        json={"decision": "acceptee"},
        headers=admin_ministeriel_headers,
    )
    assert decision.status_code == 200

    mission_a_jour = client.get("/api/v1/mes-missions-micro-job", headers=ctx["tuteur_headers"]).json()[0]
    assert mission_a_jour["statut"] == "remboursee"


def test_validation_tacite_apres_le_delai(
    client, classe_avec_enseignant_et_eleve, kkiapay_secret, db_session
):
    from app.modules.micro_jobs.models import MissionMicroJob

    ctx = classe_avec_enseignant_et_eleve
    offre, mission = _offre_acceptee(client, ctx, kkiapay_secret)
    client.post(f"/api/v1/missions-micro-job/{mission['id']}/declarer-fin", headers=ctx["enseignant_headers"])

    mission_db = db_session.get(MissionMicroJob, mission["id"])
    mission_db.date_limite_validation = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    refus_contestation = client.post(
        f"/api/v1/missions-micro-job/{mission['id']}/contester",
        json={"motif": "Trop tard"},
        headers=ctx["tuteur_headers"],
    )
    assert refus_contestation.status_code == 409

    mission_a_jour = client.get("/api/v1/mes-missions-micro-job", headers=ctx["tuteur_headers"]).json()[0]
    assert mission_a_jour["statut"] == "validee"
