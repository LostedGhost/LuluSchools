import threading
import time
from collections import deque

from fastapi import Request, status

from app.core.config import settings
from app.core.deps import api_error


class LimiteurFenetreGlissante:
    """Limiteur en memoire, par cle, sur fenetre glissante. Suffisant pour le deploiement
    actuel (un seul worker uvicorn sur Render, ADR-006) ; a remplacer par un stockage
    partage si la plateforme passe un jour sur plusieurs instances."""

    def __init__(self) -> None:
        self._evenements: dict[str, deque[float]] = {}
        self._verrou = threading.Lock()

    def _purger(self, file: deque[float], maintenant: float, fenetre: float) -> None:
        while file and maintenant - file[0] > fenetre:
            file.popleft()

    def depasse(self, cle: str, maximum: int, fenetre_secondes: float) -> bool:
        maintenant = time.monotonic()
        with self._verrou:
            file = self._evenements.get(cle)
            if file is None:
                return False
            self._purger(file, maintenant, fenetre_secondes)
            return len(file) >= maximum

    def enregistrer(self, cle: str) -> None:
        with self._verrou:
            self._evenements.setdefault(cle, deque()).append(time.monotonic())
            if len(self._evenements) > 50_000:
                self._evenements.clear()

    def reinitialiser(self, cle: str | None = None) -> None:
        with self._verrou:
            if cle is None:
                self._evenements.clear()
            else:
                self._evenements.pop(cle, None)


limiteur = LimiteurFenetreGlissante()


def adresse_client(request: Request) -> str:
    """Derriere le proxy Render (et le rewrite Vercel), l'IP reelle est le premier
    maillon de X-Forwarded-For. Falsifiable par un appel direct au service Render : les
    limites par identifiant (non falsifiables) restent donc la protection principale."""
    transmis = request.headers.get("x-forwarded-for")
    if transmis:
        return transmis.split(",")[0].strip()
    return request.client.host if request.client else "inconnu"


def verifier_limite(cle: str, maximum: int, fenetre_secondes: float) -> None:
    if not settings.rate_limit_enabled:
        return
    if limiteur.depasse(cle, maximum, fenetre_secondes):
        raise api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "trop_de_tentatives",
            "Trop de tentatives. Veuillez patienter quelques minutes avant de reessayer.",
        )


def consommer(cle: str, maximum: int, fenetre_secondes: float) -> None:
    """Verifie puis compte une tentative (pour les actions limitees a chaque appel,
    succes ou echec : inscription, renvoi de code, mot de passe oublie)."""
    verifier_limite(cle, maximum, fenetre_secondes)
    if settings.rate_limit_enabled:
        limiteur.enregistrer(cle)


def enregistrer_echec(cle: str) -> None:
    if settings.rate_limit_enabled:
        limiteur.enregistrer(cle)
