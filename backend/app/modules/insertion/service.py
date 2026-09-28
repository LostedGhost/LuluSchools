"""Lot 7.8 — regles partagees : classe actuelle d'un eleve, eligibilite a une bourse
scientifique (PAG : « programme de bourses d'etudes favorisant les filieres scientifiques »)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.etablissements.models import Classe, Etablissement
from app.modules.evaluations import periodes as periodes_evaluation
from app.modules.evaluations.router import notes_de_la_periode
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription

SEUIL_BOURSE_SUR_100 = 60.0  # 12 sur 20
_MOTS_SCIENTIFIQUES = (
    "math", "physique", "chimie", "pct", "svt", "sciences de la vie", "biologie", "informatique",
    "algorithm", "statistique", "electronique", "electrotechnique", "mecanique", "genie",
)


def _simple(texte: str) -> str:
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()


def est_matiere_scientifique(matiere: str) -> bool:
    simple = _simple(matiere)
    return any(mot in simple for mot in _MOTS_SCIENTIFIQUES)


def classe_actuelle(db: Session, eleve: Eleve) -> Classe | None:
    inscription = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )
    return db.get(Classe, inscription.classe_id) if inscription else None


@dataclass
class EligibiliteBourse:
    eligible: bool
    moyenne_sur_20: float | None
    seuil_sur_20: float
    matieres: list[str]
    explication: str


def eligibilite_bourse_scientifique(db: Session, eleve: Eleve) -> EligibiliteBourse:
    """Moyenne ponderee des seules matieres scientifiques sur toutes les periodes de
    l'annee de la classe actuelle. Aucune note scientifique = non eligible (pas encore)."""
    seuil = SEUIL_BOURSE_SUR_100 / 5
    classe = classe_actuelle(db, eleve)
    if classe is None:
        return EligibiliteBourse(False, None, seuil, [], "Aucune inscription validée cette année.")
    etab = db.get(Etablissement, classe.etablissement_id)
    notes = [
        note
        for periode in periodes_evaluation.periodes(etab.type, classe.annee_academique)
        for note in notes_de_la_periode(db, eleve, classe.id, periode.code)
        if est_matiere_scientifique(note[0])
    ]
    poids = sum(c for _, _, c in notes)
    matieres = sorted({m for m, _, _ in notes})
    if not poids:
        return EligibiliteBourse(False, None, seuil, [], "Aucune note dans une matière scientifique pour l'instant.")
    moyenne = round(sum(n * c for _, n, c in notes) / poids / 5, 2)
    texte = f"{moyenne:g}".replace(".", ",")
    if moyenne >= seuil:
        return EligibiliteBourse(True, moyenne, seuil, matieres, f"Moyenne scientifique de {texte}/20 : éligible.")
    return EligibiliteBourse(
        False, moyenne, seuil, matieres, f"Moyenne scientifique de {texte}/20 : il faut au moins {seuil:g}/20."
    )
