"""Verrouille le handler de secours ajoute dans app/main.py : sans lui, toute exception
non prevue (bug reel, IndexError sur une reponse FreeLLM malformee, etc.) atterrissait
sur le handler par defaut de Starlette - une reponse SANS la forme {"error": {...}} du
contrat, que le frontend ne sait pas interpreter (voir tests/test_llm_core.py pour le
bug concret qui a motive ce filet de secours)."""

from fastapi.testclient import TestClient

from app.main import app


def test_exception_non_geree_renvoie_la_forme_error_du_contrat(client):
    @app.get("/api/v1/__test-crash__")
    def _route_qui_plante():
        raise RuntimeError("boom")

    try:
        # raise_server_exceptions=False : le TestClient par defaut re-leve toute
        # exception non geree cote test plutot que de passer par le handler enregistre
        # (garde-fou anti-regression de pytest lui-meme) - on veut ici verifier
        # precisement ce que reçoit un vrai client HTTP (navigateur, axios), qui ne voit
        # jamais la stack Python et depend entierement du handler.
        with TestClient(app, raise_server_exceptions=False) as client_sans_relance:
            reponse = client_sans_relance.get("/api/v1/__test-crash__")
        assert reponse.status_code == 500
        corps = reponse.json()
        assert corps["error"]["code"] == "erreur_interne"
        assert "message" in corps["error"]
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/api/v1/__test-crash__"]
