from fastapi import WebSocket


class GestionnaireConnexionsLive:
    """Registre en memoire des connexions WebSocket ouvertes par session live - un seul
    process (pas de Redis/pub-sub inter-instances) : suffisant pour cette V2, a revoir si
    la plateforme tourne un jour sur plusieurs instances (voir cahier des charges, risque
    R2/R5). Les mutations passent par les endpoints REST habituels (persistance,
    permissions, validation) ; ce gestionnaire ne fait QUE diffuser l'evenement resultant
    aux clients deja connectes - aucune logique metier ici."""

    def __init__(self) -> None:
        self._connexions: dict[str, list[tuple[WebSocket, str]]] = {}

    async def connecter(self, session_id: str, websocket: WebSocket, utilisateur_id: str) -> None:
        await websocket.accept()
        self._connexions.setdefault(session_id, []).append((websocket, utilisateur_id))

    def deconnecter(self, session_id: str, websocket: WebSocket) -> None:
        restantes = [(ws, uid) for ws, uid in self._connexions.get(session_id, []) if ws is not websocket]
        if restantes:
            self._connexions[session_id] = restantes
        else:
            self._connexions.pop(session_id, None)

    async def diffuser(self, session_id: str, message: dict, exclure: WebSocket | None = None) -> None:
        for websocket, _ in list(self._connexions.get(session_id, [])):
            if websocket is exclure:
                continue
            try:
                await websocket.send_json(message)
            except Exception:
                continue

    async def envoyer_a(self, session_id: str, utilisateur_id: str, message: dict) -> None:
        for websocket, uid in list(self._connexions.get(session_id, [])):
            if uid == utilisateur_id:
                try:
                    await websocket.send_json(message)
                except Exception:
                    continue


gestionnaire_live = GestionnaireConnexionsLive()
