"""Moderation assistee par l'IA (simplification A+/A++).

Chaque signalement (message, annonce) est trie par FreeLLM des sa creation, en
arriere-plan : gravite, resume en une phrase, decision suggeree. L'administrateur voit la
file triee par gravite et peut appliquer les suggestions en lot. L'IA ne tranche jamais
seule : c'est l'administrateur qui clique (Art. 401), et une suggestion "examiner" n'est
jamais appliquee en lot.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import sessionmaker

from app.core.llm import AssistanceAdminError, FreeLLMClient

logger = logging.getLogger(__name__)

LIBELLES_DECISION = {
    "classer": "Classé sans suite après examen.",
    "masquer": "Contenu jugé inapproprié : retiré, rappel des règles adressé à l'auteur.",
}
ORDRE_GRAVITE = {"elevee": 0, "moyenne": 1, "faible": 2, None: 3}


def trier_en_arriere_plan(session_factory: sessionmaker, modele, signalement_id: str, llm_client: FreeLLMClient,
                          contenu: str, contexte: str) -> None:
    db = session_factory()
    try:
        signalement = db.get(modele, signalement_id)
        if signalement is None or signalement.traite:
            return
        try:
            triage = llm_client.trier_signalement(contenu, contexte)
        except AssistanceAdminError:
            logger.info("moderation: triage IA indisponible pour %s %s", modele.__name__, signalement_id)
            return
        signalement.ia_gravite = triage["gravite"]
        signalement.ia_resume = triage["resume"]
        signalement.ia_decision = triage["decision"]
        db.commit()
    finally:
        db.close()
