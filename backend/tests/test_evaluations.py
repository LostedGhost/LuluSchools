from datetime import datetime, timedelta, timezone

from app.core.security import decode_token


def _extraire_sub(ctx) -> str:
    token = ctx["eleve_headers"]["Authorization"].split(" ")[1]
    return decode_token(token)["sub"]


def _creer_devoir(client, ctx, date_limite, matiere="Mathematiques", bareme="flexible"):
    return client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/devoirs",
        json={
            "titre": "Devoir de maths",
            "matiere": matiere,
            "date_limite": date_limite.isoformat(),
            "bareme": bareme,
            "questions": [
                {"enonce": "Combien font 1+1 ?", "bareme_reponse": "La reponse attendue est 2.", "points_max": 10},
                {"enonce": "Combien font 2+2 ?", "bareme_reponse": "La reponse attendue est 4.", "points_max": 10},
            ],
        },
        headers=ctx["enseignant_headers"],
    ).json()


def _soumettre(client, ctx, devoir):
    return client.post(
        f"/api/v1/devoirs/{devoir['id']}/soumissions",
        json={
            "reponses": [
                {"question_id": devoir["questions"][0]["id"], "texte_reponse": "2"},
                {"question_id": devoir["questions"][1]["id"], "texte_reponse": "4"},
            ]
        },
        headers=ctx["eleve_headers"],
    )


def _soumettre_et_relire(client, ctx, devoir):
    """La correction IA part desormais en arriere-plan (BackgroundTasks) : la reponse de
    POST reflete l'etat juste avant traitement (statut=en_correction). Le test relit la
    soumission ensuite (avec TestClient, la tache d'arriere-plan s'execute avant que ce
    GET ne soit atteint)."""
    response = _soumettre(client, ctx, devoir)
    assert response.status_code == 201
    return client.get(f"/api/v1/soumissions/{response.json()['id']}", headers=ctx["eleve_headers"])


def test_soumission_corrigee_automatiquement_par_le_llm(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    devoir = _creer_devoir(client, ctx, datetime.now(timezone.utc) + timedelta(days=1))

    soumission = _soumettre_et_relire(client, ctx, devoir)
    assert soumission.status_code == 200
    body = soumission.json()
    assert body["statut"] == "corrigee"
    assert body["note"] == 20.0  # 2 questions x 10 points, le fake LLM accorde tous les points

    liste = client.get(f"/api/v1/classes/{ctx['classe']['id']}/devoirs", headers=ctx["eleve_headers"])
    assert liste.status_code == 200
    assert len(liste.json()) == 1

    ma_soumission = client.get(f"/api/v1/devoirs/{devoir['id']}/ma-soumission", headers=ctx["eleve_headers"])
    assert ma_soumission.status_code == 200
    assert ma_soumission.json()["id"] == body["id"]


def test_revision_manuelle_apres_echec_de_correction(client, fake_llm_client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    devoir = _creer_devoir(client, ctx, datetime.now(timezone.utc) + timedelta(days=1))
    fake_llm_client.questions_en_echec_correction = {"Combien font 1+1 ?"}

    soumission = _soumettre_et_relire(client, ctx, devoir).json()
    assert soumission["statut"] == "echec_correction"
    assert soumission["note"] is None

    a_revoir = client.get(f"/api/v1/devoirs/{devoir['id']}/soumissions-a-revoir", headers=ctx["enseignant_headers"])
    assert a_revoir.status_code == 200
    assert len(a_revoir.json()) == 1

    correction = client.post(
        f"/api/v1/soumissions/{soumission['id']}/corriger",
        json={
            "reponses": [
                {"question_id": devoir["questions"][0]["id"], "points_obtenus": 7},
                {"question_id": devoir["questions"][1]["id"], "points_obtenus": 10},
            ]
        },
        headers=ctx["enseignant_headers"],
    )
    assert correction.status_code == 200
    assert correction.json()["statut"] == "corrigee"
    assert correction.json()["note"] == 17.0


def test_soumission_en_retard_est_refusee(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    devoir = _creer_devoir(client, ctx, datetime.now(timezone.utc) - timedelta(minutes=1))

    response = _soumettre(client, ctx, devoir)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "delai_depasse"


def test_bulletin_compte_zero_pour_devoir_sans_soumission(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    _creer_devoir(client, ctx, datetime.now(timezone.utc) - timedelta(days=2))

    bulletin = client.get(
        f"/api/v1/eleves/{_extraire_sub(ctx)}/bulletins",
        params={"classe_id": ctx["classe"]["id"], "periode": "trimestre1"},
        headers=ctx["admin_headers"],
    )
    assert bulletin.status_code == 200
    assert bulletin.json()["moyenne_generale"] == 0.0


def test_bulletin_pondere_par_les_coefficients(client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    niveau = ctx["classe"]["niveau"]

    client.post(
        "/api/v1/referentiels-coefficients",
        json={"niveau": niveau, "matiere": "Mathematiques", "coefficient": 3},
        headers=admin_ministeriel_headers,
    )
    client.post(
        "/api/v1/referentiels-coefficients",
        json={"niveau": niveau, "matiere": "Sport", "coefficient": 1},
        headers=admin_ministeriel_headers,
    )

    # Devoir de maths : 20/20 (100%), poids 3. Devoir de sport : deja clos, sans
    # soumission -> 0%, poids 1. Moyenne attendue : (100*3 + 0*1) / 4 = 75.
    devoir_maths = _creer_devoir(client, ctx, datetime.now(timezone.utc) + timedelta(days=1), matiere="Mathematiques")
    _soumettre(client, ctx, devoir_maths)
    client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/devoirs",
        json={
            "titre": "Devoir de sport",
            "matiere": "Sport",
            "date_limite": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "bareme": "flexible",
            "questions": [{"enonce": "Decris un echauffement.", "bareme_reponse": "N/A", "points_max": 10}],
        },
        headers=ctx["enseignant_headers"],
    )

    bulletin = client.get(
        f"/api/v1/eleves/{_extraire_sub(ctx)}/bulletins",
        params={"classe_id": ctx["classe"]["id"], "periode": "trimestre1"},
        headers=ctx["admin_headers"],
    )
    assert bulletin.status_code == 200
    assert bulletin.json()["moyenne_generale"] == 75.0


def test_valider_passage_sur_le_bulletin(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    devoir = _creer_devoir(client, ctx, datetime.now(timezone.utc) + timedelta(days=1))
    _soumettre(client, ctx, devoir)
    # Le devoir doit etre clos pour compter au bulletin : on en cree un deuxieme deja clos.
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
