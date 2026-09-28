"""Lot 7.2 : preferences d'accessibilite synchronisees et lecture a voix haute pour tous."""

from app.modules.identite.models import RoleUtilisateur

from tests.conftest import creer_utilisateur_direct, token_pour


def _headers(db_session, role=RoleUtilisateur.TUTEUR, login="parent.a11y@example.com"):
    utilisateur = creer_utilisateur_direct(db_session, role=role, login_id=login)
    return {"Authorization": f"Bearer {token_pour(utilisateur)}"}


def test_preferences_par_defaut_puis_enregistrees_et_exposees_sur_me(client, db_session):
    headers = _headers(db_session)
    defaut = client.get("/api/v1/me/preferences-accessibilite", headers=headers)
    assert defaut.status_code == 200
    assert defaut.json()["taille"] == "normal" and defaut.json()["mode_ecoute"] is False

    prefs = {
        "taille": "tres_grand",
        "contraste": True,
        "espacement": True,
        "animations_reduites": True,
        "donnees": "reduit",
        "mode_ecoute": True,
        "langue_audio": "fon",
    }
    assert client.put("/api/v1/me/preferences-accessibilite", json=prefs, headers=headers).json() == prefs
    # Suit la personne sur un autre appareil : relu par /me des la connexion.
    assert client.get("/api/v1/me", headers=headers).json()["preferences_accessibilite"] == prefs


def test_preferences_valeur_inconnue_refusee(client, db_session):
    headers = _headers(db_session)
    reponse = client.put("/api/v1/me/preferences-accessibilite", json={"taille": "geant"}, headers=headers)
    assert reponse.status_code == 422
    reponse = client.put("/api/v1/me/preferences-accessibilite", json={"inconnu": 1}, headers=headers)
    assert reponse.status_code == 422


def test_preferences_exigent_une_connexion(client):
    assert client.get("/api/v1/me/preferences-accessibilite").status_code == 401


def test_lecture_a_voix_haute_ouverte_a_tous_les_roles(client, db_session, fake_llm_client):
    # Avant ce lot, seuls eleve/enseignant/tuteur (El Professor) pouvaient faire lire un texte.
    for i, role in enumerate([RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL, RoleUtilisateur.TUTEUR]):
        headers = _headers(db_session, role=role, login=f"voix{i}@example.com")
        reponse = client.post("/api/v1/accessibilite/synthese-vocale", json={"texte": "Bonjour"}, headers=headers)
        assert reponse.status_code == 200
        assert reponse.headers["content-type"] == "audio/wav"
    fake_llm_client.echec_synthese_vocale = True
    echec = client.post("/api/v1/accessibilite/synthese-vocale", json={"texte": "Bonjour"}, headers=headers)
    assert echec.status_code == 502


def test_lecture_a_voix_haute_texte_borne(client, db_session):
    headers = _headers(db_session)
    trop_long = client.post("/api/v1/accessibilite/synthese-vocale", json={"texte": "a" * 4001}, headers=headers)
    assert trop_long.status_code == 422
