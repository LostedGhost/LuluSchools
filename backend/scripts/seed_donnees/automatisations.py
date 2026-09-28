"""Etat que produisent, en usage reel, les automatisations de l'administration
(simplification A+/A++ du 2026-09-28), applique au jeu de donnees :

- actes a modele (attestation de scolarite, releve de notes) : livres automatiquement des
  le paiement, donc jamais EN_TRAITEMENT ni rejetes par un humain ;
- remboursements passes : effectues (Kkiapay), ils ne reapparaissent pas dans « A traiter » ;
- signalements et litiges en attente : deja tries / commentes par l'IA ;
- reclamations : avis de l'IA joint.
"""

from __future__ import annotations

from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.billetterie.models import BilletEvenement, StatutBillet
from app.modules.marketplace.models import (
    ContestationMarketplace,
    SignalementAnnonceMarketplace,
    StatutContestationMarketplace,
    StatutTransactionMarketplace,
    TransactionMarketplace,
)
from app.modules.messagerie.models import SignalementMessage
from app.modules.recrutement.automatisation import TENTATIVES_MAX
from app.modules.recrutement.models import DocumentCandidature, StatutDocument
from app.modules.micro_jobs.models import ContestationMicroJob, MissionMicroJob, StatutContestationMicroJob, StatutMissionMicroJob
from app.modules.services_scolaires.models import StatutTicket, TicketCantine, TicketTransport

from .contexte import Contexte

MODELES = {"Attestation de scolarité": "attestation_scolarite", "Relevé de notes": "releve_notes"}
# Les messages et annonces du seed sont anodins : le triage de l'IA le dit (un seul reste a examiner).
TRIAGE_MESSAGE = ("faible", "Message ordinaire de la vie de classe, aucun propos déplacé.", "classer")
TRIAGE_ANNONCE = ("moyenne", "Prix inhabituel pour cet article : vérifier que l'annonce est authentique.", "examiner")


def appliquer(ctx: Contexte) -> None:
    types = {t.id: t for t in ctx.objets(TypeActeAcademique)}
    for t in types.values():
        t.modele_document = MODELES.get(t.nom)
    for d in ctx.objets(DemandeActeAcademique):
        t = types.get(d.type_acte_id)
        if t is not None and t.modele_document and d.statut in (StatutDemandeActe.EN_TRAITEMENT, StatutDemandeActe.REJETEE):
            d.statut, d.motif_rejet = StatutDemandeActe.ACCEPTEE, None
            d.document_final_lulufiles_id = ctx.fichiers.acte(t.nom)
        if d.est_reclamation:
            d.analyse_ia = (
                "**Réclamation partiellement fondée.** La question 2 applique correctement la méthode du cours "
                "mais la justification finale manque : un point supplémentaire serait défendable. Le reste de la "
                "notation est conforme au barème."
            )

    # Echec de notation : la renotation automatique a deja fait ses essais.
    for doc in ctx.objets(DocumentCandidature):
        if doc.statut == StatutDocument.ECHEC_NOTATION:
            doc.tentatives_notation = TENTATIVES_MAX

    for modele, statut in ((TicketTransport, StatutTicket.REMBOURSE), (TicketCantine, StatutTicket.REMBOURSE),
                           (BilletEvenement, StatutBillet.REMBOURSE), (TransactionMarketplace, StatutTransactionMarketplace.REMBOURSEE),
                           (MissionMicroJob, StatutMissionMicroJob.REMBOURSEE)):
        for r in ctx.objets(modele):
            if r.statut == statut and r.paiement_confirme:
                r.remboursement_effectue = True

    for s in ctx.objets(SignalementMessage):
        if not s.traite:
            s.ia_gravite, s.ia_resume, s.ia_decision = TRIAGE_MESSAGE
    for s in ctx.objets(SignalementAnnonceMarketplace):
        if not s.traite:
            s.ia_gravite, s.ia_resume, s.ia_decision = TRIAGE_ANNONCE

    for c in ctx.objets(ContestationMarketplace):
        if c.statut == StatutContestationMarketplace.EN_ATTENTE:
            c.ia_decision = "acceptee"
            c.ia_justification = "L'état décrit par l'acheteur contredit l'annonce ; vérifier la photo fournie avant de rembourser."
    for c in ctx.objets(ContestationMicroJob):
        if c.statut == StatutContestationMicroJob.EN_ATTENTE:
            c.ia_decision = "rejetee"
            c.ia_justification = "Le travail a été livré dans les délais ; la contestation porte sur des attentes absentes de l'offre."
