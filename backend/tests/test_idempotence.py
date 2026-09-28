"""Lot 7.5 (UC-80) : un envoi rejoue depuis la file d'attente hors ligne n'a jamais de double effet."""

import uuid


def _conversation(client, ctx):
    eleve_id = client.get("/api/v1/me", headers=ctx["eleve_headers"]).json()["id"]
    return client.post("/api/v1/conversations", json={"participant_id": eleve_id}, headers=ctx["tuteur_headers"]).json()["id"]


def test_meme_cle_meme_reponse_un_seul_message(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    conversation_id = _conversation(client, ctx)
    url = f"/api/v1/conversations/{conversation_id}/messages"
    cle = str(uuid.uuid4())
    en_tetes = {**ctx["tuteur_headers"], "X-Cle-Idempotence": cle}
    premier = client.post(url, json={"contenu": "Bonjour, envoyé hors ligne"}, headers=en_tetes)
    rejeu = client.post(url, json={"contenu": "Bonjour, envoyé hors ligne"}, headers=en_tetes)
    assert premier.status_code == rejeu.status_code == 201
    assert rejeu.json()["id"] == premier.json()["id"]
    assert rejeu.headers.get("x-idempotence-rejeu") == "1"
    messages = client.get(url, headers=ctx["tuteur_headers"]).json()
    assert sum(1 for m in messages if m["contenu"] == "Bonjour, envoyé hors ligne") == 1

    # Une autre cle = un autre envoi ; une cle ne vaut que pour son utilisateur.
    client.post(url, json={"contenu": "Bonjour, envoyé hors ligne"}, headers={**ctx["tuteur_headers"], "X-Cle-Idempotence": str(uuid.uuid4())})
    assert sum(1 for m in client.get(url, headers=ctx["tuteur_headers"]).json() if m["contenu"] == "Bonjour, envoyé hors ligne") == 2


def test_echec_non_memorise_et_cle_invalide_ignoree(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    conversation_id = _conversation(client, ctx)
    url = f"/api/v1/conversations/{conversation_id}/messages"
    cle = str(uuid.uuid4())
    en_tetes = {**ctx["tuteur_headers"], "X-Cle-Idempotence": cle}
    assert client.post(url, json={"contenu": ""}, headers=en_tetes).status_code == 422
    # L'echec n'est pas fige : le meme envoi corrige passe ensuite.
    assert client.post(url, json={"contenu": "Corrigé"}, headers=en_tetes).status_code == 201
    invalide = client.post(url, json={"contenu": "Clé invalide"}, headers={**ctx["tuteur_headers"], "X-Cle-Idempotence": "pas-un-uuid"})
    assert invalide.status_code == 201
