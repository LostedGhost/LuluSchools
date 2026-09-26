import io

from app.core.security import decode_token


def test_declarer_rentree_ferme_la_precedente_et_inviter_tuteurs(
    client, etablissement_avec_classe, fake_email_client
):
    etab_id = etablissement_avec_classe["etablissement"]["id"]
    admin_headers = etablissement_avec_classe["admin_headers"]

    premiere = client.post(
        f"/api/v1/etablissements/{etab_id}/rentrees", json={"annee_academique": "2026-2027"}, headers=admin_headers
    )
    assert premiere.status_code == 201
    assert premiere.json()["statut"] == "ouverte"

    seconde = client.post(
        f"/api/v1/etablissements/{etab_id}/rentrees", json={"annee_academique": "2027-2028"}, headers=admin_headers
    )
    assert seconde.status_code == 201

    liste = client.get(f"/api/v1/etablissements/{etab_id}/rentrees", headers=admin_headers).json()
    statuts = {r["annee_academique"]: r["statut"] for r in liste}
    assert statuts["2026-2027"] == "fermee"
    assert statuts["2027-2028"] == "ouverte"

    invitation = client.post(
        f"/api/v1/etablissements/{etab_id}/rentrees/{seconde.json()['id']}/inviter-tuteurs", headers=admin_headers
    )
    assert invitation.status_code == 200
    # Aucun eleve encore inscrit dans cet etablissement fraichement cree.
    assert invitation.json()["nb_tuteurs_notifies"] == 0


def test_creer_classe_avec_filiere_et_annee_resolue_depuis_la_rentree_ouverte(client, etablissement_avec_classe):
    etab_id = etablissement_avec_classe["etablissement"]["id"]
    admin_headers = etablissement_avec_classe["admin_headers"]
    client.post(f"/api/v1/etablissements/{etab_id}/rentrees", json={"annee_academique": "2030-2031"}, headers=admin_headers)

    classe = client.post(
        f"/api/v1/etablissements/{etab_id}/classes",
        json={"niveau": "6ème", "filiere": "A", "capacite": 40, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    )
    assert classe.status_code == 201
    assert classe.json()["annee_academique"] == "2030-2031"
    assert classe.json()["filiere"] == "A"


def test_reconduire_classes_duplique_la_structure_pas_les_eleves(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    etab_id = ctx["etablissement"]["id"]
    classe_id = ctx["classe"]["id"]

    reconduction = client.post(
        f"/api/v1/etablissements/{etab_id}/classes/reconduire",
        json={"classe_ids": [classe_id], "nouvelle_annee": "2099-2100"},
        headers=ctx["admin_headers"],
    )
    assert reconduction.status_code == 200
    nouvelle = reconduction.json()[0]
    assert nouvelle["annee_academique"] == "2099-2100"
    assert nouvelle["reconduite_depuis_id"] == classe_id
    assert nouvelle["niveau"] == ctx["classe"]["niveau"]

    eleves_nouvelle_classe = client.get(
        f"/api/v1/etablissements/{etab_id}/console/eleves",
        params={"classe_id": nouvelle["id"]},
        headers=ctx["admin_headers"],
    ).json()
    assert eleves_nouvelle_classe["total"] == 0


def test_vie_scolaire_refusee_sans_inscription_puis_autorisee(
    client, classe_avec_enseignant_et_eleve, fake_email_client, admin_ministeriel_headers
):
    ctx = classe_avec_enseignant_et_eleve
    eleve_utilisateur_id = decode_token(ctx["eleve_headers"]["Authorization"].split(" ")[1])["sub"]

    # Un second etablissement, jamais sollicite par cet eleve, ne doit rien pouvoir lire.
    autre_etab = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Etablissement sans lien",
            "type": "EP",
            "statut": "public",
            "admin": {"nom": "Sans", "prenom": "Lien", "email": "sans.lien.vie-scolaire@example.com"},
            "latitude": 6.4,
            "longitude": 2.4,
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "sans.lien.vie-scolaire@example.com"
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "sans.lien.vie-scolaire@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    autre_admin_headers = {"Authorization": f"Bearer {login['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mot_de_passe_temp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=autre_admin_headers,
    )

    refus = client.get(f"/api/v1/eleves/{eleve_utilisateur_id}/vie-scolaire", headers=autre_admin_headers)
    assert refus.status_code == 403

    autorise = client.get(f"/api/v1/eleves/{eleve_utilisateur_id}/vie-scolaire", headers=ctx["admin_headers"])
    assert autorise.status_code == 200
    corps = autorise.json()
    assert len(corps["inscriptions"]) >= 1
    assert corps["est_etudiant"] is False
    assert corps["photo_url"] is None  # eleve EP/ES, jamais de photo meme si renseignee


def test_console_eleves_et_enseignants_filtrable_par_classe(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    etab_id = ctx["etablissement"]["id"]
    classe_id = ctx["classe"]["id"]

    eleves = client.get(
        f"/api/v1/etablissements/{etab_id}/console/eleves", params={"classe_id": classe_id}, headers=ctx["admin_headers"]
    )
    assert eleves.status_code == 200
    assert eleves.json()["total"] == 1

    enseignants = client.get(
        f"/api/v1/etablissements/{etab_id}/console/enseignants", params={"classe_id": classe_id}, headers=ctx["admin_headers"]
    )
    assert enseignants.status_code == 200
    assert enseignants.json()["total"] == 1

    tuteurs = client.get(
        f"/api/v1/etablissements/{etab_id}/console/tuteurs", params={"classe_id": classe_id}, headers=ctx["admin_headers"]
    )
    assert tuteurs.status_code == 200
    assert tuteurs.json()["total"] == 1

    # Sans filtre classe : l'etablissement entier (au moins la meme classe).
    tout_etablissement = client.get(f"/api/v1/etablissements/{etab_id}/console/eleves", headers=ctx["admin_headers"])
    assert tout_etablissement.json()["total"] >= 1


def test_poste_avec_formulaire_dynamique_exige_les_champs_requis(client, etablissement_avec_classe, enseignant_headers):
    etab_id = etablissement_avec_classe["etablissement"]["id"]
    admin_headers = etablissement_avec_classe["admin_headers"]

    poste = client.post(
        f"/api/v1/etablissements/{etab_id}/postes",
        json={
            "titre": "Professeur de mathematiques",
            "description": "Poste a pourvoir pour la rentree.",
            "matiere": "Mathematiques",
            "remuneration_min": 80000,
            "remuneration_max": 120000,
            "schema_formulaire": [
                {"id": "disponibilite", "label": "Disponibilite", "type": "texte_court", "requis": True},
                {"id": "pretentions", "label": "Pretentions salariales", "type": "texte_court", "requis": False},
            ],
            "criteres": [{"type_document": "cv", "coefficient": 1, "seuil_minimal": 0}],
        },
        headers=admin_headers,
    )
    assert poste.status_code == 201
    assert poste.json()["matiere"] == "Mathematiques"

    # casier_judiciaire est requis par le endpoint existant - fourni ici pour isoler
    # l'erreur testee (reponses_formulaire manquant) plutot qu'un 422 sur autre chose.
    sans_reponse = client.post(
        f"/api/v1/postes/{poste.json()['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"contenu"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    )
    assert sans_reponse.status_code == 422
    assert sans_reponse.json()["error"]["code"] == "reponses_formulaire_requises"

    avec_reponse = client.post(
        f"/api/v1/postes/{poste.json()['id']}/candidatures",
        data={"types": ["cv"], "reponses_formulaire": '{"disponibilite": "Immediate"}'},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"contenu"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    )
    assert avec_reponse.status_code == 201
    assert avec_reponse.json()["reponses_formulaire"] == {"disponibilite": "Immediate"}


def test_acte_avec_formulaire_dynamique_piece_jointe_et_livraison_document(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    etab_id = ctx["etablissement"]["id"]

    type_acte = client.post(
        f"/api/v1/etablissements/{etab_id}/types-actes",
        json={
            "nom": "Attestation de scolarite",
            "prix": 0,
            "pieces_requises": "Aucune",
            "schema_formulaire": [
                {"id": "motif", "label": "Motif de la demande", "type": "texte_court", "requis": True},
                {"id": "justificatif", "label": "Justificatif", "type": "fichier", "requis": True},
            ],
        },
        headers=ctx["admin_headers"],
    )
    assert type_acte.status_code == 201

    demande = client.post(
        "/api/v1/demandes-actes",
        json={"type_acte_id": type_acte.json()["id"], "reponses_formulaire": {"motif": "Bourse d'etudes"}},
        headers=ctx["eleve_headers"],
    )
    assert demande.status_code == 201
    assert demande.json()["statut"] == "en_traitement"  # gratuit, pas de paiement a attendre

    piece = client.post(
        f"/api/v1/demandes-actes/{demande.json()['id']}/pieces/justificatif",
        files={"fichier": ("piece.pdf", io.BytesIO(b"contenu-piece"), "application/pdf")},
        headers=ctx["eleve_headers"],
    )
    assert piece.status_code == 200
    assert "justificatif" in piece.json()["reponses_formulaire"]

    traitement = client.post(
        f"/api/v1/demandes-actes/{demande.json()['id']}/traiter",
        json={"decision": "acceptee"},
        headers=ctx["admin_headers"],
    )
    assert traitement.status_code == 200

    livraison = client.post(
        f"/api/v1/demandes-actes/{demande.json()['id']}/livrer-document",
        files={"fichier": ("attestation.pdf", io.BytesIO(b"le-document-final"), "application/pdf")},
        headers=ctx["admin_headers"],
    )
    assert livraison.status_code == 200
    assert livraison.json()["document_final_lulufiles_id"] is not None

    telechargement = client.get(
        f"/api/v1/demandes-actes/{demande.json()['id']}/lien-document", headers=ctx["eleve_headers"]
    )
    assert telechargement.status_code == 200
    assert "url" in telechargement.json()
