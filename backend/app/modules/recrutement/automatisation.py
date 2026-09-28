"""Recrutement : ce qui ne demande plus l'intervention de l'A+ (simplification).

- Renotation automatique : un document que FreeLLM n'a pas pu noter est retente
  (jusqu'a TENTATIVES_MAX fois, toutes les heures) avant de basculer pour de bon en
  revision manuelle - la plupart des echecs sont des indisponibilites passageres.
- Recrutement en un clic : contrat pre-rempli (syllabus redige par l'IA, echeance en fin
  d'annee scolaire). Le verdict sur le casier reste humain (Art. 395 : donnees penales,
  jamais envoyees a l'IA) et reste exige par creer_contrat.
- Reconduction groupee des contrats arrivant a echeance.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx
from sqlalchemy.orm import Session, sessionmaker

from app.core.conversion import convertir_en_image
from app.core.documents import DocumentIllisibleError, telecharger_borne
from app.core.files import FileStorageError, LuluFilesClient
from app.core.llm import AssistanceAdminError, DocumentScoringError, FreeLLMClient
from app.modules.etablissements.models import Etablissement, annee_academique_courante
from app.modules.recrutement.models import (
    Candidature,
    Contrat,
    DocumentCandidature,
    Poste,
    PropositionReconduction,
    StatutContrat,
    StatutDocument,
    StatutProposition,
)

logger = logging.getLogger(__name__)

TENTATIVES_MAX = 3
MAX_DOCUMENT_OCTETS = 20 * 1024 * 1024


def _type_contenu(contenu: bytes) -> str:
    if contenu.startswith(b"%PDF"):
        return "application/pdf"
    if contenu.startswith(b"\x89PNG"):
        return "image/png"
    return "image/jpeg"


def renoter_documents(db: Session, llm_client: FreeLLMClient, files_client: LuluFilesClient,
                      candidature_id: str | None = None) -> int:
    """Retente la notation IA des documents en echec. Renvoie le nombre de documents notes."""
    from app.modules.recrutement.router import _reevaluer_candidature  # import tardif : evite le cycle

    requete = db.query(DocumentCandidature).filter(
        DocumentCandidature.statut == StatutDocument.ECHEC_NOTATION,
        DocumentCandidature.lulufiles_file_id.isnot(None),
        DocumentCandidature.tentatives_notation < TENTATIVES_MAX,
    )
    if candidature_id is not None:
        requete = requete.filter(DocumentCandidature.candidature_id == candidature_id)
    notes = 0
    candidatures_touchees = set()
    for document in requete.all():
        document.tentatives_notation += 1
        try:
            contenu = telecharger_borne(files_client.get_signed_link(document.lulufiles_file_id), MAX_DOCUMENT_OCTETS)
            image, type_image = convertir_en_image(contenu, _type_contenu(contenu))
            document.note_ia = llm_client.noter_document(image, type_image, critere=f"conformite du document '{document.type_document}'")
            document.statut = StatutDocument.NOTE
            notes += 1
            candidatures_touchees.add(document.candidature_id)
        except (DocumentScoringError, FileStorageError, DocumentIllisibleError, httpx.HTTPError):
            logger.info("renotation: document %s toujours non notable (tentative %s)", document.id, document.tentatives_notation)
        db.commit()
    for cid in candidatures_touchees:
        candidature = db.get(Candidature, cid)
        poste = db.get(Poste, candidature.poste_id)
        _reevaluer_candidature(db, candidature, {c.type_document: c for c in poste.criteres})
    db.commit()
    return notes


def renoter_tache(session_factory: sessionmaker, llm_client: FreeLLMClient, files_client: LuluFilesClient) -> None:
    """Tache planifiee (APScheduler, voir main.py)."""
    db = session_factory()
    try:
        n = renoter_documents(db, llm_client, files_client)
        if n:
            logger.info("renotation: %s document(s) note(s) automatiquement.", n)
    except Exception:
        logger.exception("renotation automatique en echec")
    finally:
        db.close()


def echeance_fin_annee() -> date:
    """30 juin de l'annee scolaire en cours."""
    return date(int(annee_academique_courante().split("-")[1]), 6, 30)


def syllabus_propose(db: Session, llm_client: FreeLLMClient, poste: Poste) -> str:
    etablissement = db.get(Etablissement, poste.etablissement_id)
    try:
        return llm_client.rediger_syllabus(poste.titre, poste.matiere, etablissement.nom)
    except AssistanceAdminError:
        return (
            f"Enseignement : {poste.titre}"
            + (f" ({poste.matiere})" if poste.matiere else "")
            + ". Volume horaire et programme conformes au référentiel national ; organisation des évaluations "
            "et saisie des notes et de la vie scolaire sur LuluSchools."
        )


def reconduire_en_lot(db: Session, etablissement_id: str, fenetre_jours: int) -> list[PropositionReconduction]:
    """Une proposition de reconduction (nouveau contrat a signer, meme syllabus, un an de
    plus) pour chaque contrat SIGNE de l'etablissement qui arrive a echeance et n'en a pas
    encore - exactement ce que fait proposer_reconduction, en une seule fois."""
    limite = date.today() + timedelta(days=fenetre_jours)
    deja = {p.contrat_precedent_id for p in db.query(PropositionReconduction).all()}
    propositions = []
    for contrat in db.query(Contrat).filter(
        Contrat.etablissement_id == etablissement_id, Contrat.statut == StatutContrat.SIGNE, Contrat.date_fin <= limite,
        Contrat.date_fin >= date.today(),
    ).all():
        if contrat.id in deja:
            continue
        nouveau = Contrat(
            candidature_id=contrat.candidature_id, enseignant_id=contrat.enseignant_id,
            etablissement_id=contrat.etablissement_id, syllabus=contrat.syllabus,
            date_fin=contrat.date_fin.replace(year=contrat.date_fin.year + 1), statut=StatutContrat.EN_ATTENTE_SIGNATURE,
        )
        db.add(nouveau)
        db.flush()
        proposition = PropositionReconduction(contrat_precedent_id=contrat.id, nouveau_contrat_id=nouveau.id,
                                              statut=StatutProposition.EN_ATTENTE)
        db.add(proposition)
        propositions.append(proposition)
    db.commit()
    return propositions
