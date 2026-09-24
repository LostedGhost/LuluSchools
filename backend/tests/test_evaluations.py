import io
from datetime import datetime, timedelta, timezone

from app.core.security import decode_token


def _extraire_sub(ctx) -> str:
    token = ctx["eleve_headers"]["Authorization"].split(" ")[1]
    return decode_token(token)["sub"]


def _creer_devoir(client, ctx, date_limite):
    return client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/devoirs",
        json={"titre": "Devoir de maths", "date_limite": date_limite.isoformat(), "bareme": "flexible"},
        headers=ctx["enseignant_headers"],
    ).json()


def test_soumission_a_temps_puis_correction(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    devoir = _creer_devoir(client, ctx, datetime.now(timezone.utc) + timedelta(days=1))

    soumission = client.post(
        f"/api/v1/devoirs/{devoir['id']}/soumissions",
        files={"fichier": ("devoir.pdf", io.BytesIO(b"contenu"), "application/pdf")},
        headers=ctx["eleve_headers"],
    )
    assert soumission.status_code == 201
    assert soumission.json()["statut"] == "a_temps"
    assert soumission.json()["note"] is None

    correction = client.post(
        f"/api/v1/soumissions/{soumission.json()['id']}/corriger",
        json={"note": 75},
        headers=ctx["enseignant_headers"],
    )
    assert correction.status_code == 200
    assert correction.json()["note"] == 75
    assert correction.json()["statut"] == "corrigee"


def test_soumission_en_retard_est_refusee(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    devoir = _creer_devoir(client, ctx, datetime.now(timezone.utc) - timedelta(minutes=1))

    response = client.post(
        f"/api/v1/devoirs/{devoir['id']}/soumissions",
        files={"fichier": ("devoir.pdf", io.BytesIO(b"contenu"), "application/pdf")},
        headers=ctx["eleve_headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "delai_depasse"


def test_bulletin_compte_zero_pour_devoir_sans_soumission(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    # Devoir deja clos (date_limite passee), aucune soumission : doit compter 0 dans la moyenne.
    _creer_devoir(client, ctx, datetime.now(timezone.utc) - timedelta(days=2))

    bulletin = client.get(
        f"/api/v1/eleves/{_extraire_sub(ctx)}/bulletins",
        params={"classe_id": ctx["classe"]["id"], "periode": "trimestre1"},
        headers=ctx["admin_headers"],
    )
    assert bulletin.status_code == 200
    assert bulletin.json()["moyenne_generale"] == 0.0


def test_valider_passage_sur_le_bulletin(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    _creer_devoir(client, ctx, datetime.now(timezone.utc) - timedelta(days=1))
    eleve_utilisateur_id = _extraire_sub(ctx)

    bulletin = client.get(
        f"/api/v1/eleves/{eleve_utilisateur_id}/bulletins",
        params={"classe_id": ctx["classe"]["id"], "periode": "trimestre1"},
        headers=ctx["admin_headers"],
    ).json()

    response = client.post(
        f"/api/v1/bulletins/{bulletin['id']}/valider-passage",
        json={"decision": "passage"},
        headers=ctx["enseignant_headers"],
    )
    assert response.status_code == 200
    assert response.json()["valide_par_conseil"] is True
    assert response.json()["decision_passage"] == "passage"


def test_gouvernance_referentiel_coefficient(client, admin_ministeriel_headers, etablissement_avec_classe):
    referentiel = client.post(
        "/api/v1/referentiels-coefficients",
        json={"niveau": "CE1", "matiere": "Mathematiques", "coefficient": 2},
        headers=admin_ministeriel_headers,
    )
    assert referentiel.status_code == 201
    referentiel_id = referentiel.json()["id"]

    proposition_refusee = client.post(
        f"/api/v1/referentiels-coefficients/{referentiel_id}/proposition",
        json={"coefficient": 3},
        headers=admin_ministeriel_headers,
    )
    assert proposition_refusee.status_code == 403  # role A++ pas A+

    proposition = client.post(
        f"/api/v1/referentiels-coefficients/{referentiel_id}/proposition",
        json={"coefficient": 3},
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert proposition.status_code == 201
    assert proposition.json()["statut"] == "proposition_en_attente"

    validation = client.post(
        f"/api/v1/referentiels-coefficients/{proposition.json()['id']}/valider",
        headers=admin_ministeriel_headers,
    )
    assert validation.status_code == 200
    assert validation.json()["statut"] == "valide"
