"""Avis de l'IA sur un litige (marketplace : arbitre A+ ; micro-jobs : arbitre A++).

Des qu'une contestation est deposee, FreeLLM lit les faits (objet de la vente ou de la
mission, prix, dates, motif du plaignant) et prepare une recommandation motivee. L'arbitre
la voit dans sa file et tranche en un clic - la recommandation ne s'applique jamais seule.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import sessionmaker

from app.core.llm import AssistanceAdminError, FreeLLMClient

logger = logging.getLogger(__name__)


def _faits_marketplace(db, contestation) -> str:
    from app.modules.marketplace.models import AnnonceMarketplace, TransactionMarketplace

    transaction = db.get(TransactionMarketplace, contestation.transaction_id)
    annonce = db.get(AnnonceMarketplace, transaction.annonce_id)
    return (
        f"Vente entre étudiants. Annonce : {annonce.titre} — etat annonce : {annonce.etat.value} — prix : {transaction.prix_paye:g} FCFA.\n"
        f"Description du vendeur : <texte_vendeur>{annonce.description}</texte_vendeur>\n"
        f"Remise déclarée par le vendeur le {transaction.date_remise_declaree:%d/%m/%Y}.\n"
        f"Motif de la contestation de l'acheteur : <texte_acheteur>{contestation.motif}</texte_acheteur>"
    )


def _faits_micro_job(db, contestation) -> str:
    from app.modules.micro_jobs.models import MissionMicroJob, OffreMicroJob

    mission = db.get(MissionMicroJob, contestation.mission_id)
    offre = db.get(OffreMicroJob, mission.offre_id)
    return (
        f"Micro-job (service entre membres). Offre : {offre.titre} — prix : {mission.prix_paye:g} FCFA.\n"
        f"Description du client : <texte_client>{offre.description}</texte_client>\n"
        f"Fin déclarée par le prestataire le {mission.date_declaration_fin:%d/%m/%Y}.\n"
        f"Motif de la contestation du client : <texte_client>{contestation.motif}</texte_client>"
    )


def recommander_en_arriere_plan(session_factory: sessionmaker, modele, contestation_id: str, llm_client: FreeLLMClient) -> None:
    db = session_factory()
    try:
        contestation = db.get(modele, contestation_id)
        if contestation is None:
            return
        faits = _faits_marketplace(db, contestation) if hasattr(contestation, "transaction_id") else _faits_micro_job(db, contestation)
        try:
            avis = llm_client.recommander_litige(faits)
        except AssistanceAdminError:
            logger.info("litiges: avis IA indisponible pour %s %s", modele.__name__, contestation_id)
            return
        contestation.ia_decision = avis["decision"]
        contestation.ia_justification = avis["justification"]
        db.commit()
    finally:
        db.close()
