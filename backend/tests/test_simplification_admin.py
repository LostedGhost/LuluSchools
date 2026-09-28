"""Simplification du travail de l'A+ et de l'A++ : actions groupees, automatisations et
aides de l'IA (qui preparent, sans jamais trancher seules)."""

import io

from test_marketplace import _creer_annonce, _payer_via_webhook, kkiapay_secret, marketplace_ctx  # noqa: F401

from app.modules.recrutement import automatisation


# ─── Inscriptions ────────────────────────────────────────────────────────────

def _inscrire(client, tuteur_headers, classe_id, prenom):
    return client.post(
        "/api/v1/inscriptions",
        json={"nom": "Hounkpe", "prenom": prenom, "date_naissance": "2005-03-01", "classe_id": classe_id},
        headers=tuteur_headers,
    ).json()


def test_validation_en_lot_dans_la_limite_des_places(client, etablissement_avec_classe, tuteur_headers):
    ctx = etablissement_avec_classe  # classe de capacite 1
    a = _inscrire(client, tuteur_headers, ctx["classe"]["id"], "Ayaba")
    b = _inscrire(client, tuteur_headers, ctx["classe"]["id"], "Bio")
    r = client.post("/api/v1/inscriptions/valider-en-lot", json={"inscription_ids": [b["id"], a["id"]]}, headers=ctx["admin_headers"]).json()
    assert r["validees"] == [a["id"]]  # la plus ancienne d'abord
    assert r["refusees"][0]["code"] == "classe_complete"

    rejet = client.post("/api/v1/inscriptions/rejeter-en-lot", json={"inscription_ids": [b["id"]], "motif": "Classe complete"},
                        headers=ctx["admin_headers"]).json()
    assert rejet["validees"] == [b["id"]]


def test_admission_automatique(client, etablissement_avec_classe, tuteur_headers):
    ctx = etablissement_avec_classe
    reglage = client.patch(f"/api/v1/etablissements/{ctx['etablissement']['id']}/parametres",
                           json={"admission_automatique": True}, headers=ctx["admin_headers"])
    assert reglage.json()["admission_automatique"] is True
    admise = _inscrire(client, tuteur_headers, ctx["classe"]["id"], "Codjo")
    assert admise["statut"] == "validee"
    # Classe pleine : l'inscription attend simplement l'A+, elle n'est jamais refusee automatiquement.
    en_attente = _inscrire(client, tuteur_headers, ctx["classe"]["id"], "Dansou")
    assert en_attente["statut"] == "soumise"


# ─── Actes ───────────────────────────────────────────────────────────────────

def test_attestation_generee_et_livree_automatiquement(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    type_acte = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/types-actes",
        json={"nom": "Attestation de scolarité", "prix": 0, "pieces_requises": "Aucune", "modele_document": "attestation_scolarite"},
        headers=ctx["admin_headers"],
    ).json()
    demande = client.post("/api/v1/demandes-actes", json={"type_acte_id": type_acte["id"]}, headers=ctx["eleve_headers"])
    assert demande.status_code == 201
    livree = client.get("/api/v1/mes-demandes-actes", headers=ctx["eleve_headers"]).json()[0]
    assert livree["statut"] == "acceptee" and livree["document_final_lulufiles_id"]


def test_reclamation_analysee_par_l_ia(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    client.post("/api/v1/demandes-actes", json={"est_reclamation": True, "reference_evaluation": "Devoir inexistant", "motif": "Note injuste"},
                headers=ctx["eleve_headers"])
    demande = client.get("/api/v1/mes-demandes-actes", headers=ctx["eleve_headers"]).json()[0]
    assert "retrouvé" in demande["analyse_ia"]  # devoir introuvable : l'A+ examine a la main


# ─── Recrutement ─────────────────────────────────────────────────────────────

def _candidature(client, ctx, enseignant_headers, fake_llm_client):
    fake_llm_client.score_par_defaut = 85.0
    poste = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/postes",
        json={"titre": "Professeur de mathematiques", "matiere": "Mathematiques",
              "criteres": [{"type_document": "cv", "coefficient": 1, "seuil_minimal": 50}]},
        headers=ctx["admin_headers"],
    ).json()
    candidature = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures", data={"types": ["cv"]},
        files=[("fichiers", ("cv.png", io.BytesIO(b"cv"), "image/png")),
               ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"%PDF casier"), "application/pdf"))],
        headers=enseignant_headers,
    ).json()
    return poste, candidature


def test_recrutement_en_un_clic_apres_verdict_humain(client, etablissement_avec_classe, enseignant_headers, fake_llm_client):
    ctx = etablissement_avec_classe
    _, candidature = _candidature(client, ctx, enseignant_headers, fake_llm_client)
    refus = client.post(f"/api/v1/candidatures/{candidature['id']}/recruter", headers=ctx["admin_headers"])
    assert refus.status_code == 409 and refus.json()["error"]["code"] == "casier_non_verifie"
    client.post(f"/api/v1/candidatures/{candidature['id']}/casier-judiciaire/verdict", json={"conforme": True}, headers=ctx["admin_headers"])
    contrat = client.post(f"/api/v1/candidatures/{candidature['id']}/recruter", headers=ctx["admin_headers"])
    assert contrat.status_code == 201
    assert contrat.json()["syllabus"] == fake_llm_client.syllabus
    assert contrat.json()["date_fin"].endswith("-06-30")


def test_renotation_automatique_des_documents_en_echec(client, db_session, etablissement_avec_classe, enseignant_headers,
                                                     fake_llm_client, fake_files_client, monkeypatch):
    ctx = etablissement_avec_classe
    fake_llm_client.types_en_echec = {"cv"}
    _, candidature = _candidature(client, ctx, enseignant_headers, fake_llm_client)
    fake_llm_client.types_en_echec = set()
    monkeypatch.setattr(automatisation, "telecharger_borne", lambda url, maximum: b"\x89PNG image")
    relancee = client.post(f"/api/v1/candidatures/{candidature['id']}/renoter", headers=ctx["admin_headers"])
    assert relancee.status_code == 200
    assert relancee.json()["score"] == 85.0


# ─── Affectations ────────────────────────────────────────────────────────────

def test_proposition_d_affectations_appliquee_en_un_clic(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    etab_id = ctx["etablissement"]["id"]
    nouvelle = client.post(f"/api/v1/etablissements/{etab_id}/classes",
                           json={"niveau": "CE2", "capacite": 20, "politique_depassement": "ordre_arrivee"}, headers=ctx["admin_headers"]).json()
    propositions = client.get(f"/api/v1/etablissements/{etab_id}/affectations/proposition", headers=ctx["admin_headers"]).json()
    ligne = next(p for p in propositions if p["classe_id"] == nouvelle["id"])
    assert ligne["principal"] is True
    r = client.post(f"/api/v1/etablissements/{etab_id}/affectations/appliquer", json={"lignes": propositions}, headers=ctx["admin_headers"])
    assert r.json()["affectations_creees"] >= 1
    affectations = client.get(f"/api/v1/classes/{nouvelle['id']}/affectations", headers=ctx["admin_headers"]).json()
    assert affectations[0]["est_professeur_principal"] is True


# ─── Moderation ──────────────────────────────────────────────────────────────

def test_signalement_trie_par_l_ia_puis_traite_en_lot(client, classe_avec_enseignant_et_eleve, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    conversations = client.get("/api/v1/conversations", headers=ctx["eleve_headers"]).json()
    groupe = next(c for c in conversations if c["type"] == "groupe_classe")
    message = client.post(f"/api/v1/conversations/{groupe['id']}/messages", json={"contenu": "Tu es nul"}, headers=ctx["eleve_headers"]).json()
    fake_llm_client.triage_signalement = {"gravite": "moyenne", "resume": "Moquerie.", "decision": "examiner"}
    signalement = client.post(f"/api/v1/messages/{message['id']}/signaler", headers=ctx["enseignant_headers"]).json()
    a_traiter = client.get("/api/v1/administration/a-traiter", headers=ctx["admin_headers"]).json()
    section = next(s for s in a_traiter if s["cle"] == "signalements_messages")
    assert section["elements"][0]["ia_niveau"] == "moyenne"

    # Suggestion « examiner » : jamais appliquee en lot sans decision explicite.
    r = client.post("/api/v1/signalements/traiter-en-lot", json={"signalement_ids": [signalement["id"]]}, headers=ctx["admin_headers"]).json()
    assert r["ignores"] == [signalement["id"]]
    r = client.post("/api/v1/signalements/traiter-en-lot", json={"signalement_ids": [signalement["id"]], "decision": "Avertissement donné."},
                    headers=ctx["admin_headers"]).json()
    assert r["traites"] == [signalement["id"]]


# ─── Litiges, remboursements, reversements ───────────────────────────────────

def _vente_remise(client, ctx, secret, prix="5000"):
    annonce = _creer_annonce(client, ctx["vendeur_headers"], ctx["etablissement"]["id"], prix=prix).json()
    transaction = client.post(f"/api/v1/marketplace/annonces/{annonce['id']}/reserver", headers=ctx["acheteur_headers"]).json()
    client.post(f"/api/v1/marketplace/transactions/{transaction['id']}/paiement/amorcer",
                json={"transaction_id": f"tx-{transaction['id']}"}, headers=ctx["acheteur_headers"])
    _payer_via_webhook(client, f"tx-{transaction['id']}", secret, float(prix))
    client.post(f"/api/v1/marketplace/transactions/{transaction['id']}/declarer-remise", headers=ctx["vendeur_headers"])
    return transaction


def test_litige_avis_ia_et_remboursement_kkiapay_automatique(marketplace_ctx, client, kkiapay_secret, fake_kkiapay_client):  # noqa: F811
    ctx = marketplace_ctx
    transaction = _vente_remise(client, ctx, kkiapay_secret)
    contestation = client.post(f"/api/v1/marketplace/transactions/{transaction['id']}/contester",
                               json={"motif": "Article non conforme"}, headers=ctx["acheteur_headers"]).json()
    file = client.get(f"/api/v1/etablissements/{ctx['etablissement']['id']}/marketplace/contestations-en-attente", headers=ctx["admin_headers"]).json()
    assert file[0]["ia_decision"] == "acceptee" and file[0]["ia_justification"]
    client.post(f"/api/v1/marketplace/contestations/{contestation['id']}/decision", json={"decision": "acceptee"}, headers=ctx["admin_headers"])
    assert fake_kkiapay_client.rembourses == [f"tx-{transaction['id']}"]


def test_remboursement_kkiapay_en_echec_signale_dans_a_traiter(marketplace_ctx, client, kkiapay_secret, fake_kkiapay_client):  # noqa: F811
    ctx = marketplace_ctx
    fake_kkiapay_client.echec = True
    transaction = _vente_remise(client, ctx, kkiapay_secret)
    contestation = client.post(f"/api/v1/marketplace/transactions/{transaction['id']}/contester",
                               json={"motif": "Jamais recu"}, headers=ctx["acheteur_headers"]).json()
    client.post(f"/api/v1/marketplace/contestations/{contestation['id']}/decision", json={"decision": "acceptee"}, headers=ctx["admin_headers"])
    a_traiter = client.get("/api/v1/administration/a-traiter", headers=ctx["admin_headers"]).json()
    remboursements = next(s for s in a_traiter if s["cle"] == "remboursements")
    assert remboursements["elements"][0]["id"] == transaction["id"]


def test_reversement_groupe_par_vendeur(marketplace_ctx, client, kkiapay_secret):  # noqa: F811
    ctx = marketplace_ctx
    ids = []
    for prix in ("3000", "4500"):
        t = _vente_remise(client, ctx, kkiapay_secret, prix)
        client.post(f"/api/v1/marketplace/transactions/{t['id']}/confirmer", headers=ctx["acheteur_headers"])
        ids.append(t["id"])
    a_traiter = client.get("/api/v1/administration/a-traiter", headers=ctx["admin_headers"]).json()
    section = next(s for s in a_traiter if s["cle"] == "reversements_marketplace")
    assert len({e["groupe"] for e in section["elements"]}) == 1 and section["nombre"] == 2
    r = client.post("/api/v1/marketplace/transactions/reverser-en-lot", json={"ids": ids, "reference_paiement": "MOMO-123456"},
                    headers=ctx["admin_headers"])
    assert r.status_code == 200 and r.json()["montant_total"] == 7500


def test_boite_a_traiter_de_l_a_plus_plus(client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve):
    reponse = client.get("/api/v1/administration/a-traiter", headers=admin_ministeriel_headers)
    assert reponse.status_code == 200
    assert all({"cle", "titre", "nombre", "elements"} <= set(s) for s in reponse.json())
    assert client.get("/api/v1/administration/a-traiter", headers=classe_avec_enseignant_et_eleve["eleve_headers"]).status_code == 403
