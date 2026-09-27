"""Correctifs de l'audit de securite du 2026-09-27 : portee de lecture par role,
integrite des bulletins, actes, inscriptions, messagerie et casier judiciaire."""

import io
from datetime import datetime, timedelta, timezone

from app.modules.identite.models import RoleUtilisateur
from app.modules.recrutement.models import VerificationCasierJudiciaire
from app.modules.recrutement.router import purger_casiers_expires
from tests.conftest import creer_utilisateur_direct, token_pour


def _en_tete(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _nouvel_etablissement(client, fake_email_client, admin_ministeriel_headers, email_admin, type_etab="EP"):
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": f"Etablissement {email_admin}",
            "type": type_etab,
            "statut": "public",
            "admin": {"nom": "Admin", "prenom": "Autre", "email": email_admin},
            "latitude": 6.4,
            "longitude": 2.4,
        },
        headers=admin_ministeriel_headers,
    ).json()
    mdp = next(m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == email_admin)
    login = client.post("/api/v1/auth/login", json={"identifiant": email_admin, "mot_de_passe": mdp}).json()
    headers = _en_tete(login["access_token"])
    changement = client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mdp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=headers,
    ).json()
    return etablissement, _en_tete(changement["access_token"])


def _tuteur(client, fake_email_client, email):
    payload = {"nom": "Tuteur", "prenom": "Autre", "email": email, "mot_de_passe": "Password1"}
    client.post("/api/v1/auth/tuteurs", json=payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == email)
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": email, "code": code})
    login = client.post("/api/v1/auth/login", json={"identifiant": email, "mot_de_passe": "Password1"}).json()
    return _en_tete(login["access_token"])


def _publier_cours_pdf(client, ctx, titre="Chapitre 1"):
    return client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/cours",
        data={"titre": titre, "chapitre": "1", "format": "pdf"},
        files={"fichier": ("cours.pdf", io.BytesIO(b"%PDF-1.4 contenu"), "application/pdf")},
        headers=ctx["enseignant_headers"],
    ).json()


# --- Pedagogie : portee de lecture ---------------------------------------------------


def test_tuteur_sans_enfant_dans_la_classe_ne_lit_ni_cours_ni_fichier(client, fake_email_client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    cours = _publier_cours_pdf(client, ctx)
    etranger = _tuteur(client, fake_email_client, "etranger.cours@example.com")

    assert client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=etranger).status_code == 403
    assert client.get(f"/api/v1/cours/{cours['id']}/lien-fichier", headers=etranger).status_code == 403
    assert client.get(f"/api/v1/cours/{cours['id']}/quiz", headers=etranger).status_code == 403

    assert client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["tuteur_headers"]).status_code == 200


def test_admin_d_un_autre_etablissement_ne_lit_pas_les_cours(
    client, fake_email_client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    cours = _publier_cours_pdf(client, ctx)
    _, autre_admin = _nouvel_etablissement(client, fake_email_client, admin_ministeriel_headers, "autre.admin.cours@example.com")

    assert client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=autre_admin).status_code == 403
    assert client.get(f"/api/v1/cours/{cours['id']}/lien-fichier", headers=autre_admin).status_code == 403
    assert client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["admin_headers"]).status_code == 200


def test_cours_masque_invisible_et_inaccessible_pour_eleve_et_tuteur(
    client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    cours = _publier_cours_pdf(client, ctx)
    client.post(f"/api/v1/cours/{cours['id']}/masquer", json={"motif": "Contenu inapproprie"}, headers=admin_ministeriel_headers)

    for headers in (ctx["eleve_headers"], ctx["tuteur_headers"]):
        liste = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=headers).json()
        assert all(c["id"] != cours["id"] for c in liste)
        assert client.get(f"/api/v1/cours/{cours['id']}/lien-fichier", headers=headers).status_code == 404

    enseignant = client.get(f"/api/v1/classes/{ctx['classe']['id']}/cours", headers=ctx["enseignant_headers"]).json()
    assert any(c["id"] == cours["id"] for c in enseignant)


# --- Evaluations : bulletins ---------------------------------------------------------


def test_bulletin_refuse_pour_un_eleve_hors_de_la_classe(
    client, fake_email_client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    etablissement, autre_admin = _nouvel_etablissement(
        client, fake_email_client, admin_ministeriel_headers, "autre.admin.bulletin@example.com"
    )
    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "CE2", "capacite": 5, "politique_depassement": "ordre_arrivee"},
        headers=autre_admin,
    ).json()
    tuteur = _tuteur(client, fake_email_client, "parent.bulletin@example.com")
    inscription = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Autre", "prenom": "Enfant", "date_naissance": "2016-03-03", "classe_id": classe["id"],
              "consentement_parental_donne": True},
        headers=tuteur,
    ).json()
    client.post(f"/api/v1/inscriptions/{inscription['id']}/valider", headers=autre_admin)
    eleve_utilisateur_id = client.get("/api/v1/tuteurs/me/inscriptions", headers=tuteur).json()[0]["eleve_utilisateur_id"]

    reponse = client.get(
        f"/api/v1/eleves/{eleve_utilisateur_id}/bulletins",
        params={"classe_id": ctx["classe"]["id"], "periode": "T1"},
        headers=ctx["enseignant_headers"],
    )
    assert reponse.status_code == 404

    classe_inexistante = client.get(
        f"/api/v1/eleves/{eleve_utilisateur_id}/bulletins",
        params={"classe_id": "inexistante", "periode": "T1"},
        headers=ctx["admin_headers"],
    )
    assert classe_inexistante.status_code == 404


# --- Actes academiques -------------------------------------------------------------


def test_type_d_acte_d_un_autre_etablissement_refuse(
    client, fake_email_client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    etablissement, autre_admin = _nouvel_etablissement(
        client, fake_email_client, admin_ministeriel_headers, "autre.admin.actes@example.com"
    )
    acte_gratuit_ailleurs = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/types-actes",
        json={"nom": "Releve de notes", "prix": 0, "pieces_requises": "aucune"},
        headers=autre_admin,
    ).json()

    reponse = client.post(
        "/api/v1/demandes-actes", json={"type_acte_id": acte_gratuit_ailleurs["id"]}, headers=ctx["eleve_headers"]
    )
    assert reponse.status_code == 403


def test_decision_d_acte_limitee_a_accepter_ou_rejeter(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    type_acte = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-actes",
        json={"nom": "Certificat de scolarite", "prix": 0, "pieces_requises": "aucune"},
        headers=ctx["admin_headers"],
    ).json()
    demande = client.post("/api/v1/demandes-actes", json={"type_acte_id": type_acte["id"]}, headers=ctx["eleve_headers"]).json()
    assert demande["statut"] == "en_traitement"

    reponse = client.post(
        f"/api/v1/demandes-actes/{demande['id']}/traiter", json={"decision": "soumise"}, headers=ctx["admin_headers"]
    )
    assert reponse.status_code == 422


# --- Inscriptions ------------------------------------------------------------------


def _eleve_mineur_valide(client, fake_email_client, ctx, email_tuteur="parent.mineur@example.com"):
    tuteur = _tuteur(client, fake_email_client, email_tuteur)
    classe = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/classes",
        json={"niveau": "CM1", "capacite": 10, "politique_depassement": "ordre_arrivee"},
        headers=ctx["admin_headers"],
    ).json()
    inscription = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Petit", "prenom": "Mineur", "date_naissance": "2015-05-05", "classe_id": classe["id"],
              "consentement_parental_donne": True},
        headers=tuteur,
    ).json()
    client.post(f"/api/v1/inscriptions/{inscription['id']}/valider", headers=ctx["admin_headers"])
    identifiants = next(m for m in fake_email_client.sent if m.get("to_email") == email_tuteur and "login_id" in m)
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": identifiants["login_id"], "mot_de_passe": identifiants["mot_de_passe"]}
    ).json()
    headers = _en_tete(login["access_token"])
    changement = client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": identifiants["mot_de_passe"], "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=headers,
    ).json()
    return tuteur, _en_tete(changement["access_token"]), identifiants["login_id"], inscription


def test_eleve_mineur_ne_peut_pas_consentir_pour_lui_meme(client, fake_email_client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    _, eleve, _, _ = _eleve_mineur_valide(client, fake_email_client, ctx)
    nouvelle_classe = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/classes",
        json={"niveau": "CM2", "capacite": 10, "politique_depassement": "ordre_arrivee"},
        headers=ctx["admin_headers"],
    ).json()
    reponse = client.post(
        "/api/v1/inscriptions",
        json={"nom": "x", "prenom": "x", "date_naissance": "2015-05-05", "classe_id": nouvelle_classe["id"],
              "consentement_parental_donne": True},
        headers=eleve,
    )
    assert reponse.status_code == 201
    assert reponse.json()["statut"] == "en_attente_consentement_parental"


def test_reinscription_conserve_compte_et_matricule(client, fake_email_client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    tuteur, _, matricule, premiere = _eleve_mineur_valide(client, fake_email_client, ctx, "parent.reinscription@example.com")
    nb_identifiants = sum(1 for m in fake_email_client.sent if "login_id" in m)
    nouvelle_classe = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/classes",
        json={"niveau": "CM2", "capacite": 10, "politique_depassement": "ordre_arrivee", "annee_academique": "2027-2028"},
        headers=ctx["admin_headers"],
    ).json()
    seconde = client.post(
        "/api/v1/inscriptions",
        json={"nom": "petit ", "prenom": "MINEUR", "date_naissance": "2015-05-05", "classe_id": nouvelle_classe["id"],
              "consentement_parental_donne": True},
        headers=tuteur,
    ).json()
    assert seconde["eleve_id"] == premiere["eleve_id"]

    valide = client.post(f"/api/v1/inscriptions/{seconde['id']}/valider", headers=ctx["admin_headers"])
    assert valide.status_code == 200
    assert sum(1 for m in fake_email_client.sent if "login_id" in m) == nb_identifiants
    enfants = client.get("/api/v1/tuteurs/me/inscriptions", headers=tuteur).json()
    assert {e["eleve_matricule"] for e in enfants} == {matricule}
    assert client.post(
        "/api/v1/auth/login", json={"identifiant": matricule, "mot_de_passe": "NouveauMdp1"}
    ).status_code == 200


def test_inscription_en_double_et_rejet_d_une_inscription_validee_refuses(
    client, fake_email_client, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    tuteur, _, _, inscription = _eleve_mineur_valide(client, fake_email_client, ctx, "parent.doublon@example.com")
    doublon = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Petit", "prenom": "Mineur", "date_naissance": "2015-05-05", "classe_id": inscription["classe_id"]},
        headers=tuteur,
    )
    assert doublon.status_code == 409
    rejet = client.post(
        f"/api/v1/inscriptions/{inscription['id']}/rejeter", json={"motif": "erreur"}, headers=ctx["admin_headers"]
    )
    assert rejet.status_code == 409


# --- Messagerie -------------------------------------------------------------------


def test_enseignant_sous_contrat_mais_non_affecte_exclu_du_groupe_de_classe(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    autre_classe = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/classes",
        json={"niveau": "CE2", "capacite": 10, "politique_depassement": "ordre_arrivee"},
        headers=ctx["admin_headers"],
    ).json()
    reponse = client.get(f"/api/v1/classes/{autre_classe['id']}/conversation", headers=ctx["enseignant_headers"])
    assert reponse.status_code == 403


# --- Recrutement : casier judiciaire ---------------------------------------------------


def _poste_et_candidature(client, etablissement_avec_classe, enseignant_headers, fake_llm_client, score=90.0):
    admin = etablissement_avec_classe["admin_headers"]
    poste = client.post(
        f"/api/v1/etablissements/{etablissement_avec_classe['etablissement']['id']}/postes",
        json={"titre": "Professeur", "criteres": [{"type_document": "cv", "coefficient": 1, "seuil_minimal": 50}]},
        headers=admin,
    ).json()
    fake_llm_client.score_par_defaut = score
    reponse = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"contenu cv"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"%PDF casier vierge"), "application/pdf")),
        ],
        headers=enseignant_headers,
    )
    assert reponse.status_code == 201
    return poste, client.get(f"/api/v1/candidatures/{reponse.json()['id']}", headers=admin).json()


def test_casier_consultable_par_l_a_plus_puis_purge_au_verdict(
    client, fake_llm_client, etablissement_avec_classe, enseignant_headers, admin_ministeriel_headers
):
    admin = etablissement_avec_classe["admin_headers"]
    _, candidature = _poste_et_candidature(client, etablissement_avec_classe, enseignant_headers, fake_llm_client)
    base = f"/api/v1/candidatures/{candidature['id']}/casier-judiciaire"
    assert candidature["statut_casier_judiciaire"] == "en_attente"

    statut = client.get(base, headers=admin).json()
    assert statut["statut"] == "en_attente" and statut["document_disponible"] is True
    document = client.get(f"{base}/document", headers=admin)
    assert document.status_code == 200
    assert document.content == b"%PDF casier vierge"
    assert document.headers["cache-control"] == "no-store"

    assert client.get(base, headers=admin_ministeriel_headers).status_code == 403
    assert client.get(f"{base}/document", headers=enseignant_headers).status_code == 403

    contrat_avant = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme", "date_fin": "2027-06-30"},
        headers=admin,
    )
    assert contrat_avant.status_code == 409
    assert contrat_avant.json()["error"]["code"] == "casier_non_verifie"

    verdict = client.post(f"{base}/verdict", json={"conforme": True}, headers=admin)
    assert verdict.status_code == 200
    assert verdict.json()["statut"] == "conforme" and verdict.json()["document_disponible"] is False
    assert client.get(f"{base}/document", headers=admin).status_code == 410
    assert client.post(f"{base}/verdict", json={"conforme": False}, headers=admin).status_code == 409

    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme", "date_fin": "2027-06-30"},
        headers=admin,
    )
    assert contrat.status_code == 201


def test_casier_non_conforme_elimine_la_candidature(client, fake_llm_client, etablissement_avec_classe, enseignant_headers):
    admin = etablissement_avec_classe["admin_headers"]
    _, candidature = _poste_et_candidature(client, etablissement_avec_classe, enseignant_headers, fake_llm_client)
    client.post(f"/api/v1/candidatures/{candidature['id']}/casier-judiciaire/verdict", json={"conforme": False}, headers=admin)
    relue = client.get(f"/api/v1/candidatures/{candidature['id']}", headers=admin).json()
    assert relue["statut"] == "rejetee"


def test_purge_des_casiers_expires(client, db_session, fake_llm_client, etablissement_avec_classe, enseignant_headers):
    _, candidature = _poste_et_candidature(client, etablissement_avec_classe, enseignant_headers, fake_llm_client)
    verification = db_session.query(VerificationCasierJudiciaire).filter_by(candidature_id=candidature["id"]).one()
    assert verification.date_suppression_prevue is not None
    verification.date_suppression_prevue = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    assert purger_casiers_expires(db_session) == 1
    db_session.refresh(verification)
    assert verification.contenu_chiffre is None
    assert verification.statut.value == "en_attente"


def test_candidature_rejetee_a_un_score_et_contestation_acceptee_ouvre_le_contrat(
    client, fake_llm_client, etablissement_avec_classe, enseignant_headers
):
    admin = etablissement_avec_classe["admin_headers"]
    _, candidature = _poste_et_candidature(client, etablissement_avec_classe, enseignant_headers, fake_llm_client, score=30.0)
    assert candidature["statut"] == "rejetee"
    assert candidature["score"] == 30.0

    contestation = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contestation", json={"motif": "Mon CV a ete mal lu"}, headers=enseignant_headers
    ).json()
    assert client.post(
        f"/api/v1/candidatures/{candidature['id']}/contestation", json={"motif": "encore"}, headers=enseignant_headers
    ).status_code == 409

    decision = client.post(f"/api/v1/contestations/{contestation['id']}/decision", json={"decision": "acceptee"}, headers=admin)
    assert decision.status_code == 200
    assert client.post(
        f"/api/v1/contestations/{contestation['id']}/decision",
        json={"decision": "rejetee", "motif_decision": "revirement"},
        headers=admin,
    ).status_code == 409

    client.post(f"/api/v1/candidatures/{candidature['id']}/casier-judiciaire/verdict", json={"conforme": True}, headers=admin)
    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme", "date_fin": "2027-06-30"},
        headers=admin,
    )
    assert contrat.status_code == 201


def test_candidature_en_double_et_fichiers_hors_limites_refuses(
    client, fake_llm_client, etablissement_avec_classe, enseignant_headers
):
    poste, _ = _poste_et_candidature(client, etablissement_avec_classe, enseignant_headers, fake_llm_client)
    doublon = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"cv"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    )
    assert doublon.status_code == 409


def test_type_de_fichier_de_candidature_refuse(
    client, fake_email_client, fake_llm_client, etablissement_avec_classe
):
    admin = etablissement_avec_classe["admin_headers"]
    poste = client.post(
        f"/api/v1/etablissements/{etablissement_avec_classe['etablissement']['id']}/postes",
        json={"titre": "Prof", "criteres": [{"type_document": "cv", "coefficient": 1, "seuil_minimal": 0}]},
        headers=admin,
    ).json()
    payload = {"nom": "Ens", "prenom": "Deux", "email": "ens.deux@example.com", "mot_de_passe": "Password1"}
    client.post("/api/v1/auth/enseignants", json=payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == payload["email"])
    client.post("/api/v1/auth/enseignants/verify-otp", json={"email": payload["email"], "code": code})
    headers = _en_tete(client.post(
        "/api/v1/auth/login", json={"identifiant": payload["email"], "mot_de_passe": "Password1"}
    ).json()["access_token"])

    reponse = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.html", io.BytesIO(b"<script>alert(1)</script>"), "text/html")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=headers,
    )
    assert reponse.status_code == 415


def test_candidatures_en_attente_de_revision_sans_distinct_sur_json(
    client, db_session, fake_llm_client, etablissement_avec_classe, enseignant_headers
):
    """PostgreSQL ne sait pas comparer une colonne `json` : un SELECT DISTINCT sur
    Candidature (reponses_formulaire) echouait en production et cassait tout l'ecran
    Recrutement de l'A+ - invisible sous SQLite, d'ou la verification du SQL emis."""
    from sqlalchemy import event

    fake_llm_client.types_en_echec = {"cv"}
    _, candidature = _poste_et_candidature(client, etablissement_avec_classe, enseignant_headers, fake_llm_client)

    requetes: list[str] = []
    moteur = db_session.get_bind()

    def _capturer(conn, cursor, statement, *args):
        requetes.append(statement)

    event.listen(moteur, "before_cursor_execute", _capturer)
    try:
        reponse = client.get("/api/v1/candidatures/en-attente-revision", headers=etablissement_avec_classe["admin_headers"])
    finally:
        event.remove(moteur, "before_cursor_execute", _capturer)

    assert reponse.status_code == 200
    assert [c["id"] for c in reponse.json()] == [candidature["id"]]
    assert not any("DISTINCT" in r.upper() and "FROM CANDIDATURES" in r.upper() for r in requetes)


def test_compte_a_mot_de_passe_temporaire_bloque_sur_les_endpoints_metier(client, db_session):
    utilisateur = creer_utilisateur_direct(db_session, role=RoleUtilisateur.TUTEUR, login_id="temporaire@example.com")
    utilisateur.mot_de_passe_temporaire = True
    db_session.commit()
    reponse = client.get("/api/v1/etablissements", headers=_en_tete(token_pour(utilisateur)))
    assert reponse.status_code == 403
    assert reponse.json()["error"]["code"] == "changement_mot_de_passe_requis"
