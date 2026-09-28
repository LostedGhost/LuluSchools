"""Lot 7.4 : mode Ecoute (phrases a lire a voix haute) et messages vocaux."""

import io
from datetime import date

from app.modules.inscriptions.models import Eleve
from app.modules.vie_scolaire.models import EntreeVieScolaire, NatureEntreeVieScolaire


def test_resume_oral_du_tuteur_sans_ia(client, classe_avec_enseignant_et_eleve, db_session, fake_llm_client):
    ctx = classe_avec_enseignant_et_eleve
    reponse = client.get("/api/v1/ecoute/tuteur", headers=ctx["tuteur_headers"])
    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees["accueil"].startswith("Bonjour Awa")
    enfant = donnees["enfants"][0]
    assert enfant["prenom"] == "Aisha"
    tuiles = {t["cle"]: t for t in enfant["tuiles"]}
    assert "pas encore de note" in tuiles["bulletin"]["phrase"]
    assert "n'a manqué aucun cours" in tuiles["presences"]["phrase"]
    assert tuiles["presences"]["alerte"] is False
    assert tuiles["devoirs"]["phrase"] == "Aisha a rendu tous ses devoirs."
    assert tuiles["bulletin"]["lien"].startswith("/tuteur/bulletins?enfant=")

    # Une absence et un retard enregistres par l'ecole s'entendent aussitot.
    eleve = db_session.query(Eleve).filter(Eleve.prenom == "Aisha").one()
    for nature in (NatureEntreeVieScolaire.ABSENCE, NatureEntreeVieScolaire.RETARD):
        db_session.add(
            EntreeVieScolaire(
                eleve_id=eleve.id, classe_id=ctx["classe"]["id"], auteur_id=eleve.utilisateur_id,
                nature=nature, description="Test", date_survenue=date.today(),
            )
        )
    db_session.commit()
    presences = next(
        t for t in client.get("/api/v1/ecoute/tuteur", headers=ctx["tuteur_headers"]).json()["enfants"][0]["tuiles"]
        if t["cle"] == "presences"
    )
    assert presences["phrase"] == "Ce mois-ci, on compte 1 absence et 1 retard pour Aisha."
    assert presences["alerte"] is True


def test_mode_ecoute_reserve_au_tuteur(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    assert client.get("/api/v1/ecoute/tuteur", headers=ctx["eleve_headers"]).status_code == 403


def _conversation_tuteur_enfant(client, ctx):
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    return client.post("/api/v1/conversations", json={"participant_id": eleve_id}, headers=ctx["tuteur_headers"]).json()["id"]


def test_message_vocal_envoye_et_ecoute_par_les_membres(client, classe_avec_enseignant_et_eleve, fake_files_client):
    ctx = classe_avec_enseignant_et_eleve
    conversation_id = _conversation_tuteur_enfant(client, ctx)
    envoi = client.post(
        f"/api/v1/conversations/{conversation_id}/messages-vocaux",
        data={"duree_secondes": "12"},
        files={"audio": ("vocal.webm", io.BytesIO(b"opus"), "audio/webm")},
        headers=ctx["tuteur_headers"],
    )
    assert envoi.status_code == 201
    message = envoi.json()
    assert message["est_vocal"] is True and message["duree_audio_s"] == 12
    assert message["contenu"] == "Message vocal (0:12)"

    fil = client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=ctx["eleve_headers"]).json()
    assert any(m["est_vocal"] for m in fil)
    lien = client.get(f"/api/v1/messages/{message['id']}/audio", headers=ctx["eleve_headers"])
    assert lien.status_code == 200 and lien.json()["url"].startswith("https://")
    # Hors de la conversation : aucun acces au fichier audio.
    assert client.get(f"/api/v1/messages/{message['id']}/audio", headers=ctx["enseignant_headers"]).status_code == 403


def test_message_vocal_type_et_duree_bornes(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    conversation_id = _conversation_tuteur_enfant(client, ctx)
    url = f"/api/v1/conversations/{conversation_id}/messages-vocaux"
    mauvais_type = client.post(
        url, data={"duree_secondes": "5"}, files={"audio": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        headers=ctx["tuteur_headers"],
    )
    assert mauvais_type.status_code == 415
    trop_long = client.post(
        url, data={"duree_secondes": "600"}, files={"audio": ("v.webm", io.BytesIO(b"opus"), "audio/webm")},
        headers=ctx["tuteur_headers"],
    )
    assert trop_long.status_code == 422
