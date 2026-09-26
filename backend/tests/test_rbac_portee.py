"""Regressions cibles pour l'audit RBAC (A++ bloque a tort / enseignant sans portee
classe / endpoints sans verification) - voir le commit qui introduit ce fichier pour
le detail des 3 chantiers corriges. Ne re-teste pas ce qui l'est deja ailleurs
(inscriptions, tuteur/enfant, etc. - couverts par les tests par module)."""

import io


def test_admin_ministeriel_peut_creer_une_classe_sans_etre_admin_de_l_etablissement(
    client, etablissement_avec_classe, admin_ministeriel_headers
):
    etablissement_id = etablissement_avec_classe["etablissement"]["id"]
    reponse = client.post(
        f"/api/v1/etablissements/{etablissement_id}/classes",
        json={"niveau": "CE2", "capacite": 10, "politique_depassement": "ordre_arrivee"},
        headers=admin_ministeriel_headers,
    )
    assert reponse.status_code == 201


def test_admin_etablissement_ne_peut_toujours_pas_creer_une_classe_ailleurs(
    client, etablissement_avec_classe, fake_email_client, admin_ministeriel_headers
):
    """Garde-fou : le chantier 1 ouvre l'acces a A++, il ne doit pas elargir A+."""
    autre_etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Autre Ecole",
            "type": "EP",
            "statut": "public",
            "admin": {"nom": "Diallo", "prenom": "Issa", "email": "issa.diallo.autre@example.com"},
            "latitude": 6.4025,
            "longitude": 2.3389,
        },
        headers=admin_ministeriel_headers,
    ).json()
    admin_headers_etab_1 = etablissement_avec_classe["admin_headers"]
    reponse = client.post(
        f"/api/v1/etablissements/{autre_etablissement['id']}/classes",
        json={"niveau": "CE2", "capacite": 10, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers_etab_1,
    )
    assert reponse.status_code == 403


def _provisionner_etablissement(client, fake_email_client, admin_ministeriel_headers, *, nom, email):
    """Cree un etablissement INDEPENDANT de la fixture `etablissement_avec_classe` (dont
    l'instance est partagee/mise en cache par pytest au sein d'un meme test) - necessaire
    pour verifier une isolation inter-etablissements avec un etablissement vraiment tiers."""
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": nom,
            "type": "EP",
            "statut": "public",
            "admin": {"nom": "Adjovi", "prenom": "Rose", "email": email},
            "latitude": 6.4969,
            "longitude": 2.6289,
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == email)
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": email, "mot_de_passe": mot_de_passe_temp}
    ).json()
    admin_headers = {"Authorization": f"Bearer {login['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mot_de_passe_temp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=admin_headers,
    )
    return {"etablissement": etablissement, "admin_headers": admin_headers}


def _provisionner_enseignant_sous_contrat(client, fake_email_client, fake_llm_client, etablissement_avec_classe, email):
    admin_headers = etablissement_avec_classe["admin_headers"]
    etablissement_id = etablissement_avec_classe["etablissement"]["id"]

    client.post(
        "/api/v1/auth/enseignants",
        json={"nom": "Zannou", "prenom": "Firmin", "email": email, "mot_de_passe": "Password1"},
    )
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == email)
    client.post("/api/v1/auth/enseignants/verify-otp", json={"email": email, "code": code})
    login = client.post("/api/v1/auth/login", json={"identifiant": email, "mot_de_passe": "Password1"}).json()
    enseignant_headers = {"Authorization": f"Bearer {login['access_token']}"}

    poste = client.post(
        f"/api/v1/etablissements/{etablissement_id}/postes",
        json={"titre": "Professeur", "criteres": [{"type_document": "cv", "coefficient": 1, "seuil_minimal": 0}]},
        headers=admin_headers,
    ).json()
    fake_llm_client.score_par_defaut = 100.0
    candidature = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"contenu"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    ).json()
    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme", "date_fin": "2027-06-30"},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/contrats/{contrat['id']}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace"), "image/png")},
        headers=enseignant_headers,
    )
    return enseignant_headers


def test_enseignant_sous_contrat_mais_sans_affectation_ne_peut_pas_publier_un_cours(
    client, etablissement_avec_classe, fake_email_client, fake_llm_client
):
    """Le coeur du chantier 3 : un contrat signe avec l'etablissement ne suffit plus,
    il faut une AffectationEnseignant sur la classe precise."""
    enseignant_headers = _provisionner_enseignant_sous_contrat(
        client, fake_email_client, fake_llm_client, etablissement_avec_classe, "firmin.sans-affectation@example.com"
    )
    classe_id = etablissement_avec_classe["classe"]["id"]

    reponse = client.post(
        f"/api/v1/classes/{classe_id}/cours",
        data={"titre": "Cours", "chapitre": "Chapitre 1", "format": "texte", "contenu_texte": "..."},
        headers=enseignant_headers,
    )
    assert reponse.status_code == 403


def test_enseignant_affecte_peut_publier_un_cours(client, etablissement_avec_classe, fake_email_client, fake_llm_client):
    admin_headers = etablissement_avec_classe["admin_headers"]
    classe_id = etablissement_avec_classe["classe"]["id"]
    enseignant_headers = _provisionner_enseignant_sous_contrat(
        client, fake_email_client, fake_llm_client, etablissement_avec_classe, "firmin.affecte@example.com"
    )
    enseignant_utilisateur_id = client.get("/api/v1/me", headers=enseignant_headers).json()["id"]

    affectation = client.post(
        f"/api/v1/classes/{classe_id}/affectations",
        json={"enseignant_utilisateur_id": enseignant_utilisateur_id},
        headers=admin_headers,
    )
    assert affectation.status_code == 201

    reponse = client.post(
        f"/api/v1/classes/{classe_id}/cours",
        data={"titre": "Cours", "chapitre": "Chapitre 1", "format": "texte", "contenu_texte": "..."},
        headers=enseignant_headers,
    )
    assert reponse.status_code == 201

    mes_classes = client.get("/api/v1/mes-classes-affectees", headers=enseignant_headers).json()
    assert [c["id"] for c in mes_classes] == [classe_id]


def test_affectation_refusee_sans_contrat_signe(client, etablissement_avec_classe, tuteur_headers):
    """Un A+ ne doit pas pouvoir affecter n'importe quel utilisateur (ex. un tuteur, ou
    un enseignant qui n'a meme pas de contrat signe avec cet etablissement)."""
    admin_headers = etablissement_avec_classe["admin_headers"]
    classe_id = etablissement_avec_classe["classe"]["id"]
    tuteur_utilisateur_id = client.get("/api/v1/me", headers=tuteur_headers).json()["id"]

    reponse = client.post(
        f"/api/v1/classes/{classe_id}/affectations",
        json={"enseignant_utilisateur_id": tuteur_utilisateur_id},
        headers=admin_headers,
    )
    assert reponse.status_code == 404


def test_obtenir_devoir_refuse_a_un_admin_d_un_autre_etablissement(
    client, classe_avec_enseignant_et_eleve, admin_ministeriel_headers, fake_email_client
):
    """Chantier 2 : cet endpoint n'avait auparavant AUCUNE verification de portee."""
    ctx = classe_avec_enseignant_et_eleve
    devoir = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/devoirs",
        json={
            "titre": "Devoir",
            "matiere": "Mathematiques",
            "date_limite": "2027-01-01T00:00:00Z",
            "bareme": "flexible",
            "questions": [{"enonce": "1+1", "bareme_reponse": "2", "points_max": 10}],
        },
        headers=ctx["enseignant_headers"],
    ).json()

    reponse = client.get(f"/api/v1/devoirs/{devoir['id']}", headers=ctx["eleve_headers"])
    assert reponse.status_code == 200

    # L'A+ d'un tout autre etablissement (sans lien avec cette classe) doit etre refuse.
    etranger = _provisionner_etablissement(
        client, fake_email_client, admin_ministeriel_headers,
        nom="Ecole Etrangere", email="rose.adjovi.etrangere@example.com",
    )
    reponse_admin_etranger = client.get(f"/api/v1/devoirs/{devoir['id']}", headers=etranger["admin_headers"])
    assert reponse_admin_etranger.status_code == 403


def test_lister_referentiels_masque_les_propositions_d_un_autre_etablissement(
    client, etablissement_avec_classe, admin_ministeriel_headers, fake_email_client
):
    """Chantier 2 : un A+ ne doit voir que les referentiels nationaux et ses propres
    propositions, jamais celles d'un etablissement concurrent."""
    admin_headers_etab_1 = etablissement_avec_classe["admin_headers"]
    referentiel = client.post(
        "/api/v1/referentiels-coefficients",
        json={"niveau": "CE1", "matiere": "Mathematiques", "coefficient": 3},
        headers=admin_ministeriel_headers,
    ).json()
    proposition = client.post(
        f"/api/v1/referentiels-coefficients/{referentiel['id']}/proposition",
        json={"coefficient": 2},
        headers=admin_headers_etab_1,
    )
    assert proposition.status_code == 201
    proposition_id = proposition.json()["id"]

    concurrent = _provisionner_etablissement(
        client, fake_email_client, admin_ministeriel_headers,
        nom="Ecole Concurrente", email="rose.adjovi.concurrente@example.com",
    )

    referentiels_vus_par_etab_2 = client.get(
        "/api/v1/referentiels-coefficients", headers=concurrent["admin_headers"]
    ).json()
    assert proposition_id not in [r["id"] for r in referentiels_vus_par_etab_2]

    referentiels_vus_par_ministere = client.get(
        "/api/v1/referentiels-coefficients", headers=admin_ministeriel_headers
    ).json()
    assert proposition_id in [r["id"] for r in referentiels_vus_par_ministere]
