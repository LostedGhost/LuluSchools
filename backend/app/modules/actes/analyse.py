"""Avis de l'IA sur une reclamation de note (aide a la decision de l'A+).

La copie de l'eleve, le bareme de chaque question, les points attribues et le motif de la
reclamation sont soumis a FreeLLM, qui redige un avis argumente (fondee / partiellement
fondee / non fondee). L'avis est affiche a l'A+, qui reste seul a trancher (Art. 401).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import sessionmaker

from app.core.llm import FreeLLMClient, ReclamationAnalyseError
from app.modules.actes.models import DemandeActeAcademique
from app.modules.evaluations.models import Devoir, ReponseSoumission, Soumission
from app.modules.inscriptions.models import Inscription, StatutInscription

logger = logging.getLogger(__name__)


def _copie(db, demande: DemandeActeAcademique) -> str | None:
    """Retrouve la copie visee par la reclamation (titre du devoir cite par l'eleve)."""
    classes = [i.classe_id for i in db.query(Inscription).filter(
        Inscription.eleve_id == demande.eleve_id, Inscription.statut == StatutInscription.VALIDEE)]
    reference = (demande.reference_evaluation or "").strip().lower()
    devoirs = db.query(Devoir).filter(Devoir.classe_id.in_(classes)).all() if classes else []
    devoir = next((d for d in devoirs if d.titre.lower() == reference), None) or next(
        (d for d in devoirs if reference and (reference in d.titre.lower() or d.titre.lower() in reference)), None)
    if devoir is None:
        return None
    soumission = db.query(Soumission).filter(Soumission.devoir_id == devoir.id, Soumission.eleve_id == demande.eleve_id).first()
    if soumission is None:
        return f"Devoir : {devoir.titre} ({devoir.matiere}). L'élève n'a pas déposé de copie pour ce devoir."
    lignes = [f"Devoir : {devoir.titre} ({devoir.matiere}) — note obtenue : {soumission.note} / "
              f"{sum(q.points_max for q in devoir.questions):g}"]
    if soumission.copie_image_lulufiles_file_id:
        lignes.append("Copie photographiée : correction globale, pas de détail par question.")
    reponses = {r.question_id: r for r in db.query(ReponseSoumission).filter(ReponseSoumission.soumission_id == soumission.id)}
    for q in sorted(devoir.questions, key=lambda q: q.ordre):
        r = reponses.get(q.id)
        lignes.append(
            f"\nQuestion {q.ordre} ({q.points_max:g} pts) : {q.enonce}\nBarème : {q.bareme_reponse}\n"
            f"Réponse de l'élève : <reponse_eleve>{r.texte_reponse if r else '(aucune)'}</reponse_eleve>\n"
            f"Points attribués : {r.points_obtenus if r and r.points_obtenus is not None else '—'}"
            + (f" — commentaire : {r.commentaire_ia}" if r and r.commentaire_ia else "")
        )
    return "\n".join(lignes)


def analyser_reclamation_en_arriere_plan(session_factory: sessionmaker, demande_id: str, llm_client: FreeLLMClient) -> None:
    db = session_factory()
    try:
        demande = db.get(DemandeActeAcademique, demande_id)
        if demande is None or not demande.est_reclamation:
            return
        copie = _copie(db, demande)
        if copie is None:
            demande.analyse_ia = (
                "Analyse automatique impossible : le devoir cité par l'élève n'a pas été retrouvé "
                f"(« {demande.reference_evaluation} »). À examiner manuellement."
            )
        else:
            try:
                demande.analyse_ia = llm_client.analyser_reclamation(copie, demande.motif or "")
            except ReclamationAnalyseError:
                logger.warning("actes: analyse IA indisponible pour la reclamation %s.", demande_id)
                return
        db.commit()
    finally:
        db.close()
