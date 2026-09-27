"""Complements de l'audit du 2026-09-27 : rattachement des paiements par partnerId,
restrictions de perimetre (messagerie, controleurs, tickets, sessions live, devoirs
masques), pagination et dedoublonnage."""

import io
from datetime import datetime, timedelta, timezone

import pytest

from app.core.reservation import aujourdhui_benin
from app.modules.inscriptions.models import Inscription, StatutInscription
from app.modules.messagerie.models import Conversation, Message
from tests.test_securite_acces import _nouvel_etablissement, _poste_et_candidature, _tuteur


@pytest.fixture()
def kkiapay_secret(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "kkiapay_secret", "secret-de-test")
    return "secret-de-test"


def _webhook(client, secret, transaction_id, montant, partner_id=None):
    corps = {"transactionId": transaction_id, "isPaymentSucces": True, "event": "transaction.success", "amount": montant}
    if partner_id is not None:
        corps["partnerId"] = partner_id
    return client.post("/api/v1/paiements/webhook/kkiapay", json=corps, headers={"x-kkiapay-secret": secret})


def _ligne_et_deux_tickets(client, ctx, prix=200):
    ligne = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/lignes-transport",
        json={"nom": "Ligne P", "prix": prix, "capacite_par_trajet": 10},
        headers=ctx["admin_headers"],
    ).json()
    jour = (aujourdhui_benin() + timedelta(days=2)).isoformat()
    lendemain = (aujourdhui_benin() + timedelta(days=3)).isoformat()
    t1 = client.post(f"/api/v1/lignes-transport/{ligne['id']}/tickets", json={"date_trajet": jour}, headers=ctx["eleve_headers"]).json()
    t2 = client.post(f"/api/v1/lignes-transport/{ligne['id']}/tickets", json={"date_trajet": lendemain}, headers=ctx["eleve_headers"]).json()
    return t1, t2


# --- Paiements : le partnerId designe la ressource payee ------------------------------


def test_webhook_confirme_la_ressource_designee_par_partner_id(client, classe_avec_enseignant_et_eleve, kkiapay_secret):
    ctx = classe_avec_enseignant_et_eleve
    victime, detournement = _ligne_et_deux_tickets(client, ctx)
    # Un identifiant de transaction intercepte est rattache a une autre ressource de meme prix...
    client.post(
        f"/api/v1/tickets-transport/{detournement['id']}/paiement/amorcer",
        json={"transaction_id": "tx-interceptee"},
        headers=ctx["eleve_headers"],
    )
    # ... mais le widget du payeur a transmis le partnerId de SA ressource : c'est elle qui est payee.
    assert _webhook(client, kkiapay_secret, "tx-interceptee", 200, f"ticket_transport:{victime['id']}").status_code == 200

    payee = client.get(f"/api/v1/tickets-transport/{victime['id']}", headers=ctx["eleve_headers"]).json()
    detournee = client.get(f"/api/v1/tickets-transport/{detournement['id']}", headers=ctx["eleve_headers"]).json()
    assert payee["paiement_confirme"] is True
    assert detournee["paiement_confirme"] is False


def test_webhook_partner_id_montant_insuffisant_refuse(client, classe_avec_enseignant_et_eleve, kkiapay_secret):
    ctx = classe_avec_enseignant_et_eleve
    ticket, _ = _ligne_et_deux_tickets(client, ctx, prix=500)
    _webhook(client, kkiapay_secret, "tx-trop-faible", 10, f"ticket_transport:{ticket['id']}")
    assert client.get(f"/api/v1/tickets-transport/{ticket['id']}", headers=ctx["eleve_headers"]).json()["paiement_confirme"] is False


def test_webhook_partner_id_inconnu_ignore(client, classe_avec_enseignant_et_eleve, kkiapay_secret):
    ctx = classe_avec_enseignant_et_eleve
    ticket, _ = _ligne_et_deux_tickets(client, ctx)
    client.post(
        f"/api/v1/tickets-transport/{ticket['id']}/paiement/amorcer",
        json={"transaction_id": "tx-partner-faux"},
        headers=ctx["eleve_headers"],
    )
    assert _webhook(client, kkiapay_secret, "tx-partner-faux", 200, "ticket_transport:inexistant").status_code == 200
    assert client.get(f"/api/v1/tickets-transport/{ticket['id']}", headers=ctx["eleve_headers"]).json()["paiement_confirme"] is False


# --- Services scolaires reserves aux eleves de l'etablissement ---------------------------


def test_ticket_transport_refuse_a_un_eleve_d_un_autre_etablissement(
    client, fake_email_client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    etablissement, autre_admin = _nouvel_etablissement(client, fake_email_client, admin_ministeriel_headers, "autre.admin.bus@example.com")
    ligne_ailleurs = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/lignes-transport",
        json={"nom": "Ligne ailleurs", "prix": 100, "capacite_par_trajet": 10},
        headers=autre_admin,
    ).json()
    reponse = client.post(
        f"/api/v1/lignes-transport/{ligne_ailleurs['id']}/tickets",
        json={"date_trajet": (aujourdhui_benin() + timedelta(days=1)).isoformat()},
        headers=ctx["eleve_headers"],
    )
    assert reponse.status_code == 403
    assert reponse.json()["error"]["code"] == "hors_etablissement"


# --- Messagerie ------------------------------------------------------------------------


def test_dm_entre_eleves_limite_au_meme_etablissement(
    client, fake_email_client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    etablissement, autre_admin = _nouvel_etablissement(client, fake_email_client, admin_ministeriel_headers, "autre.admin.dm@example.com")
    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "CE2", "capacite": 5, "politique_depassement": "ordre_arrivee"},
        headers=autre_admin,
    ).json()
    tuteur = _tuteur(client, fake_email_client, "parent.dm@example.com")
    inscription = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Ailleurs", "prenom": "Eleve", "date_naissance": "2015-01-01", "classe_id": classe["id"], "consentement_parental_donne": True},
        headers=tuteur,
    ).json()
    client.post(f"/api/v1/inscriptions/{inscription['id']}/valider", headers=autre_admin)
    eleve_ailleurs_id = client.get("/api/v1/tuteurs/me/inscriptions", headers=tuteur).json()[0]["eleve_utilisateur_id"]

    reponse = client.post("/api/v1/conversations", json={"participant_id": eleve_ailleurs_id}, headers=ctx["eleve_headers"])
    assert reponse.status_code == 403
    assert reponse.json()["error"]["code"] == "hors_etablissement"


def test_messages_pagines_et_signalement_dedoublonne(client, db_session, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    conversation = client.get(f"/api/v1/classes/{ctx['classe']['id']}/conversation", headers=ctx["eleve_headers"]).json()
    base = datetime.now(timezone.utc) - timedelta(hours=1)
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    for i in range(5):
        db_session.add(Message(conversation_id=conversation["id"], auteur_id=eleve_id, contenu=f"m{i}", created_at=base + timedelta(minutes=i)))
    db_session.commit()

    page = client.get(f"/api/v1/conversations/{conversation['id']}/messages", params={"limite": 2}, headers=ctx["eleve_headers"]).json()
    assert [m["contenu"] for m in page] == ["m4", "m3"]
    suivante = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages",
        params={"limite": 2, "avant": page[-1]["id"]},
        headers=ctx["eleve_headers"],
    ).json()
    assert [m["contenu"] for m in suivante] == ["m2", "m1"]

    premier = client.post(f"/api/v1/messages/{page[0]['id']}/signaler", headers=ctx["tuteur_headers"]).json()
    second = client.post(f"/api/v1/messages/{page[0]['id']}/signaler", headers=ctx["tuteur_headers"]).json()
    assert premier["id"] == second["id"]
    signalements = client.get(f"/api/v1/etablissements/{ctx['etablissement']['id']}/signalements", headers=ctx["admin_headers"]).json()
    assert len(signalements) == 1


# --- Controle d'acces --------------------------------------------------------------------


def test_controleur_limite_aux_comptes_de_l_etablissement(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    refus = client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": eleve_id, "service": "transport"},
        headers=ctx["admin_headers"],
    )
    assert refus.status_code == 422
    assert refus.json()["error"]["code"] == "non_designable"

    enseignant_id = client.get("/api/v1/me", headers=ctx["enseignant_headers"]).json()["id"]
    assert client.post(
        f"/api/v1/etablissements/{ctx['etablissement']['id']}/controleurs",
        json={"utilisateur_id": enseignant_id, "service": "transport"},
        headers=ctx["admin_headers"],
    ).status_code == 201


# --- Devoirs masques, sessions live, photos, revision --------------------------------------


def test_devoir_masque_inaccessible_par_lien_direct_et_non_soumettable(
    client, admin_ministeriel_headers, classe_avec_enseignant_et_eleve
):
    ctx = classe_avec_enseignant_et_eleve
    devoir = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/devoirs",
        json={
            "titre": "Devoir", "matiere": "Maths", "date_limite": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "bareme": "flexible", "nature": "sommative",
            "questions": [{"enonce": "1+1 ?", "bareme_reponse": "2", "points_max": 5}],
        },
        headers=ctx["enseignant_headers"],
    ).json()
    client.post(f"/api/v1/devoirs/{devoir['id']}/masquer", json={"motif": "Hors programme"}, headers=admin_ministeriel_headers)

    assert client.get(f"/api/v1/devoirs/{devoir['id']}", headers=ctx["eleve_headers"]).status_code == 404
    assert client.get(f"/api/v1/devoirs/{devoir['id']}", headers=ctx["tuteur_headers"]).status_code == 404
    assert client.get(f"/api/v1/devoirs/{devoir['id']}", headers=ctx["enseignant_headers"]).status_code == 200
    question_id = client.get(f"/api/v1/devoirs/{devoir['id']}/questions-bareme", headers=ctx["enseignant_headers"]).json()[0]["id"]
    soumission = client.post(
        f"/api/v1/devoirs/{devoir['id']}/soumissions",
        json={"reponses": [{"question_id": question_id, "texte_reponse": "2"}]},
        headers=ctx["eleve_headers"],
    )
    assert soumission.status_code == 404


def test_eleve_desinscrit_perd_l_acces_a_la_session_live(client, db_session, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    session = client.post(
        f"/api/v1/classes/{ctx['classe']['id']}/sessions-live",
        json={"date_heure": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
        headers=ctx["enseignant_headers"],
    ).json()
    assert client.post(f"/api/v1/sessions-live/{session['id']}/rejoindre", headers=ctx["eleve_headers"]).status_code == 200
    assert client.get(f"/api/v1/sessions-live/{session['id']}/messages", headers=ctx["eleve_headers"]).status_code == 200

    for inscription in db_session.query(Inscription).filter(Inscription.classe_id == ctx["classe"]["id"]):
        inscription.statut = StatutInscription.REJETEE
    db_session.commit()
    assert client.get(f"/api/v1/sessions-live/{session['id']}/messages", headers=ctx["eleve_headers"]).status_code == 403


def test_photos_publiques_masquees_pour_un_etablissement_suspendu(
    client, admin_ministeriel_headers, etablissement_avec_classe
):
    etab = etablissement_avec_classe["etablissement"]
    client.post(
        f"/api/v1/etablissements/{etab['id']}/photos",
        files={"fichier": ("photo.png", io.BytesIO(b"\x89PNG\r\n\x1a\nphoto"), "image/png")},
        headers=etablissement_avec_classe["admin_headers"],
    )
    assert len(client.get(f"/api/v1/etablissements/{etab['id']}/photos-publiques").json()) == 1
    client.post(
        "/api/v1/etablissements/action-groupee",
        json={"ids": [etab["id"]], "action": "suspendre", "motif": "Controle"},
        headers=admin_ministeriel_headers,
    )
    assert client.get(f"/api/v1/etablissements/{etab['id']}/photos-publiques").json() == []


def test_file_de_revision_nationale_pour_l_a_plus_plus(
    client, fake_llm_client, etablissement_avec_classe, enseignant_headers, admin_ministeriel_headers
):
    fake_llm_client.types_en_echec = {"cv"}
    _, candidature = _poste_et_candidature(client, etablissement_avec_classe, enseignant_headers, fake_llm_client)
    reponse = client.get("/api/v1/candidatures/en-attente-revision", headers=admin_ministeriel_headers)
    assert [c["id"] for c in reponse.json()] == [candidature["id"]]


def test_conversation_inconnue_pagination_repere_invalide(client, classe_avec_enseignant_et_eleve, db_session):
    ctx = classe_avec_enseignant_et_eleve
    conversation = db_session.query(Conversation).filter(Conversation.classe_id == ctx["classe"]["id"]).one()
    reponse = client.get(
        f"/api/v1/conversations/{conversation.id}/messages", params={"avant": "inexistant"}, headers=ctx["eleve_headers"]
    )
    assert reponse.status_code == 404
