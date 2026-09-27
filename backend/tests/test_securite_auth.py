from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.core.email import BrevoEmailClient
from app.modules.identite.models import ObjetOtp, OtpVerification, RoleUtilisateur, Utilisateur
from tests.conftest import creer_utilisateur_direct, token_pour

TUTEUR = {"nom": "Houngbo", "prenom": "Rita", "email": "rita.securite@example.com", "mot_de_passe": "Password1"}


def _inscrire_tuteur(client, fake_email_client, payload=TUTEUR):
    client.post("/api/v1/auth/tuteurs", json=payload)
    return next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == payload["email"])


def _tuteur_verifie(client, fake_email_client, payload=TUTEUR):
    code = _inscrire_tuteur(client, fake_email_client, payload)
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": payload["email"], "code": code})
    return client.post(
        "/api/v1/auth/login", json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]}
    ).json()


def test_compte_suspendu_ne_peut_ni_se_connecter_ni_rafraichir_ni_lire_son_profil(client, db_session):
    utilisateur = creer_utilisateur_direct(db_session, role=RoleUtilisateur.TUTEUR, login_id="suspendu@example.com")
    tokens = client.post(
        "/api/v1/auth/login", json={"identifiant": "suspendu@example.com", "mot_de_passe": "Password1"}
    ).json()
    utilisateur.actif = False
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={"identifiant": "suspendu@example.com", "mot_de_passe": "Password1"})
    assert login.status_code == 403
    assert login.json()["error"]["code"] == "compte_suspendu"

    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 403

    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token_pour(utilisateur)}"})
    assert me.status_code == 403


def test_mauvais_mot_de_passe_sur_compte_suspendu_ne_revele_pas_la_suspension(client, db_session):
    utilisateur = creer_utilisateur_direct(db_session, role=RoleUtilisateur.TUTEUR, login_id="suspendu2@example.com")
    utilisateur.actif = False
    db_session.commit()
    reponse = client.post("/api/v1/auth/login", json={"identifiant": "suspendu2@example.com", "mot_de_passe": "Mauvais1"})
    assert reponse.status_code == 401


def test_changement_de_mot_de_passe_revoque_les_anciens_refresh_tokens(client, fake_email_client):
    tokens = _tuteur_verifie(client, fake_email_client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    reponse = client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": "Password1", "nouveau_mot_de_passe": "Nouveau123"},
        headers=headers,
    )
    assert reponse.status_code == 200
    nouveaux = reponse.json()
    assert nouveaux["access_token"] and nouveaux["refresh_token"]

    ancien = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert ancien.status_code == 401
    assert ancien.json()["error"]["code"] == "session_expiree"

    nouveau = client.post("/api/v1/auth/refresh", json={"refresh_token": nouveaux["refresh_token"]})
    assert nouveau.status_code == 200


def test_nouveau_mot_de_passe_identique_refuse(client, fake_email_client):
    tokens = _tuteur_verifie(client, fake_email_client)
    reponse = client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": "Password1", "nouveau_mot_de_passe": "Password1"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert reponse.status_code == 422


def test_mot_de_passe_trop_long_refuse(client):
    reponse = client.post("/api/v1/auth/tuteurs", json={**TUTEUR, "mot_de_passe": "A1" + "x" * 200})
    assert reponse.status_code == 422


def test_login_insensible_a_la_casse_de_l_email(client, fake_email_client):
    _tuteur_verifie(client, fake_email_client)
    reponse = client.post(
        "/api/v1/auth/login", json={"identifiant": "Rita.Securite@Example.com", "mot_de_passe": "Password1"}
    )
    assert reponse.status_code == 200


def test_renvoi_otp_debloque_un_compte_dont_le_code_a_expire(client, fake_email_client, db_session):
    ancien_code = _inscrire_tuteur(client, fake_email_client)
    utilisateur = db_session.query(Utilisateur).filter(Utilisateur.email == TUTEUR["email"]).one()
    otp = db_session.query(OtpVerification).filter(OtpVerification.utilisateur_id == utilisateur.id).one()
    otp.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    expire = client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": TUTEUR["email"], "code": ancien_code})
    assert expire.json()["error"]["code"] == "otp_expire"

    renvoi = client.post("/api/v1/auth/otp/renvoyer", json={"email": TUTEUR["email"]})
    assert renvoi.status_code == 200
    nouveau_code = fake_email_client.sent[-1]["code"]

    verif = client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": TUTEUR["email"], "code": nouveau_code})
    assert verif.status_code == 200
    assert verif.json()["email_verifie"] is True


def test_renvoi_otp_reponse_identique_pour_une_adresse_inconnue(client, fake_email_client):
    reponse = client.post("/api/v1/auth/otp/renvoyer", json={"email": "personne@example.com"})
    assert reponse.status_code == 200
    assert fake_email_client.sent == []


def test_renvoi_otp_invalide_le_code_precedent(client, fake_email_client):
    ancien_code = _inscrire_tuteur(client, fake_email_client)
    client.post("/api/v1/auth/otp/renvoyer", json={"email": TUTEUR["email"]})
    reponse = client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": TUTEUR["email"], "code": ancien_code})
    assert reponse.status_code == 401


def test_mot_de_passe_oublie_tuteur(client, fake_email_client):
    anciens = _tuteur_verifie(client, fake_email_client)
    reponse = client.post("/api/v1/auth/mot-de-passe-oublie", json={"identifiant": TUTEUR["email"]})
    assert reponse.status_code == 200
    code = fake_email_client.sent[-1]["reset_code"]

    mauvais = client.post(
        "/api/v1/auth/mot-de-passe-oublie/confirmer",
        json={"identifiant": TUTEUR["email"], "code": "000000" if code != "000000" else "111111", "nouveau_mot_de_passe": "Reinit123"},
    )
    assert mauvais.status_code == 401

    ok = client.post(
        "/api/v1/auth/mot-de-passe-oublie/confirmer",
        json={"identifiant": TUTEUR["email"], "code": code, "nouveau_mot_de_passe": "Reinit123"},
    )
    assert ok.status_code == 200

    assert client.post(
        "/api/v1/auth/login", json={"identifiant": TUTEUR["email"], "mot_de_passe": "Password1"}
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"identifiant": TUTEUR["email"], "mot_de_passe": "Reinit123"}
    ).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": anciens["refresh_token"]}).status_code == 401

    rejeu = client.post(
        "/api/v1/auth/mot-de-passe-oublie/confirmer",
        json={"identifiant": TUTEUR["email"], "code": code, "nouveau_mot_de_passe": "Autre1234"},
    )
    assert rejeu.status_code == 404


def test_code_de_verification_email_inutilisable_pour_reinitialiser(client, fake_email_client):
    code_verification = _inscrire_tuteur(client, fake_email_client)
    reponse = client.post(
        "/api/v1/auth/mot-de-passe-oublie/confirmer",
        json={"identifiant": TUTEUR["email"], "code": code_verification, "nouveau_mot_de_passe": "Reinit123"},
    )
    assert reponse.status_code == 404


def test_mot_de_passe_oublie_eleve_envoie_le_code_au_tuteur(client, fake_email_client, classe_avec_enseignant_et_eleve):
    identifiants = next(m for m in fake_email_client.sent if "login_id" in m and m["to_email"] == "awa.tuteur.classe@example.com")
    reponse = client.post("/api/v1/auth/mot-de-passe-oublie", json={"identifiant": identifiants["login_id"]})
    assert reponse.status_code == 200
    envoi = fake_email_client.sent[-1]
    assert envoi["to_email"] == "awa.tuteur.classe@example.com"
    assert envoi["reset_login_id"] == identifiants["login_id"]

    ok = client.post(
        "/api/v1/auth/mot-de-passe-oublie/confirmer",
        json={"identifiant": identifiants["login_id"], "code": envoi["reset_code"], "nouveau_mot_de_passe": "Eleve1234"},
    )
    assert ok.status_code == 200
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": identifiants["login_id"], "mot_de_passe": "Eleve1234"}
    )
    assert login.status_code == 200
    assert login.json()["doit_changer_mot_de_passe"] is False


def test_mot_de_passe_oublie_identifiant_inconnu_reponse_generique(client, fake_email_client):
    reponse = client.post("/api/v1/auth/mot-de-passe-oublie", json={"identifiant": "inconnu@example.com"})
    assert reponse.status_code == 200
    assert fake_email_client.sent == []


def test_force_brute_login_bloquee(client, db_session, limitation_debit):
    creer_utilisateur_direct(db_session, role=RoleUtilisateur.TUTEUR, login_id="cible@example.com")
    for _ in range(10):
        assert client.post(
            "/api/v1/auth/login", json={"identifiant": "cible@example.com", "mot_de_passe": "Mauvais1"}
        ).status_code == 401
    bloque = client.post("/api/v1/auth/login", json={"identifiant": "cible@example.com", "mot_de_passe": "Password1"})
    assert bloque.status_code == 429
    assert bloque.json()["error"]["code"] == "trop_de_tentatives"


def test_renvoi_otp_limite_par_adresse(client, fake_email_client, limitation_debit):
    _inscrire_tuteur(client, fake_email_client)
    for _ in range(3):
        assert client.post("/api/v1/auth/otp/renvoyer", json={"email": TUTEUR["email"]}).status_code == 200
    assert client.post("/api/v1/auth/otp/renvoyer", json={"email": TUTEUR["email"]}).status_code == 429


def test_e_mails_echappent_les_donnees_saisies(monkeypatch):
    captures = []
    monkeypatch.setattr(BrevoEmailClient, "_send", lambda self, *args: captures.append(args))
    BrevoEmailClient().send_otp_email("x@example.com", '<a href="https://evil.example">Cliquez</a>', "123456")
    html = captures[0][3]
    assert "<a href" not in html
    assert "&lt;a href=" in html


def test_refus_de_demarrer_en_production_avec_un_secret_jwt_par_defaut():
    with pytest.raises(RuntimeError):
        Settings(environment="production", jwt_secret_key="change-me").verifier_configuration_production()


def test_objet_otp_par_defaut_est_la_verification_email(client, fake_email_client, db_session):
    _inscrire_tuteur(client, fake_email_client)
    otp = db_session.query(OtpVerification).one()
    assert otp.objet == ObjetOtp.VERIFICATION_EMAIL.value
