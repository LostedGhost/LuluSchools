"""Proposition automatique d'affectations (simplification A+).

Au lieu d'affecter chaque enseignant classe par classe, l'A+ recoit une proposition
calculee puis l'applique en un clic (il peut retirer des lignes avant) :
- chaque classe sans professeur principal en recoit un : de preference un enseignant deja
  affecte a la classe, sinon celui qui a le moins de classes principales ;
- chaque enseignant de matiere (matiere de son poste de recrutement) est propose sur les
  classes dont le niveau enseigne cette matiere (referentiel national des coefficients) et
  ou elle n'est encore couverte par personne, en equilibrant la charge (plafond de classes).
Seuls les enseignants sous contrat SIGNE avec l'etablissement sont proposes.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.modules.etablissements.models import AffectationEnseignant, Classe, annee_academique_courante
from app.modules.evaluations.models import ReferentielCoefficient, StatutReferentiel
from app.modules.identite.models import Utilisateur
from app.modules.recrutement.models import Candidature, Contrat, Poste, StatutContrat

CLASSES_MAX_PAR_ENSEIGNANT = 6


def enseignants_sous_contrat(db: Session, etablissement_id: str) -> dict[str, str | None]:
    """enseignant_id -> matiere du poste pour lequel il a ete recrute (None = polyvalent)."""
    lignes = (
        db.query(Contrat.enseignant_id, Poste.matiere)
        .join(Candidature, Candidature.id == Contrat.candidature_id)
        .join(Poste, Poste.id == Candidature.poste_id)
        .filter(Contrat.etablissement_id == etablissement_id, Contrat.statut == StatutContrat.SIGNE)
        .all()
    )
    return {enseignant_id: matiere for enseignant_id, matiere in lignes}


def proposer(db: Session, etablissement_id: str) -> list[dict]:
    enseignants = enseignants_sous_contrat(db, etablissement_id)
    if not enseignants:
        return []
    classes = (
        db.query(Classe)
        .filter(Classe.etablissement_id == etablissement_id, Classe.annee_academique == annee_academique_courante())
        .order_by(Classe.niveau)
        .all()
    )
    affectations = db.query(AffectationEnseignant).filter(AffectationEnseignant.classe_id.in_([c.id for c in classes])).all()
    affectes = defaultdict(set)  # classe -> enseignants
    charge = defaultdict(int)
    principaux = defaultdict(int)
    classes_avec_principal = set()
    for a in affectations:
        affectes[a.classe_id].add(a.enseignant_id)
        charge[a.enseignant_id] += 1
        if a.est_professeur_principal:
            classes_avec_principal.add(a.classe_id)
            principaux[a.enseignant_id] += 1
    matieres_niveau = defaultdict(set)
    for niveau, matiere in db.query(ReferentielCoefficient.niveau, ReferentielCoefficient.matiere).filter(
        ReferentielCoefficient.statut == StatutReferentiel.VALIDE
    ):
        matieres_niveau[niveau].add(matiere)
    noms = {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_(list(enseignants)))}

    propositions: list[dict] = []

    def proposer_ligne(classe: Classe, enseignant_id: str, principal: bool, motif: str) -> None:
        u = noms[enseignant_id]
        propositions.append({
            "classe_id": classe.id, "classe": f"{classe.niveau}" + (f" — {classe.filiere}" if classe.filiere else ""),
            "enseignant_utilisateur_id": enseignant_id, "enseignant": f"{u.prenom} {u.nom}",
            "matiere": enseignants[enseignant_id], "principal": principal, "motif": motif,
        })
        if enseignant_id not in affectes[classe.id]:
            affectes[classe.id].add(enseignant_id)
            charge[enseignant_id] += 1
        if principal:
            principaux[enseignant_id] += 1
            classes_avec_principal.add(classe.id)

    # 1. Matieres non couvertes
    for enseignant_id, matiere in sorted(enseignants.items(), key=lambda kv: charge[kv[0]]):
        if matiere is None:
            continue
        candidates = [c for c in classes if matiere in matieres_niveau.get(c.niveau, set())
                      and not any(enseignants.get(e) == matiere for e in affectes[c.id])]
        for classe in sorted(candidates, key=lambda c: len(affectes[c.id])):
            if charge[enseignant_id] >= CLASSES_MAX_PAR_ENSEIGNANT:
                break
            proposer_ligne(classe, enseignant_id, False, f"{matiere} n'est encore enseignée par personne dans cette classe")

    # 2. Professeurs principaux manquants
    for classe in classes:
        if classe.id in classes_avec_principal:
            continue
        deja = [e for e in affectes[classe.id] if e in enseignants]
        vivier = deja or [e for e in enseignants if charge[e] < CLASSES_MAX_PAR_ENSEIGNANT] or list(enseignants)
        choisi = min(vivier, key=lambda e: (principaux[e], charge[e]))
        # Une ligne deja proposee a l'etape 1 pour ce couple devient simplement "principale".
        ligne = next((p for p in propositions if p["classe_id"] == classe.id and p["enseignant_utilisateur_id"] == choisi), None)
        if ligne:
            ligne["principal"] = True
            ligne["motif"] += " ; classe sans professeur principal"
            principaux[choisi] += 1
            classes_avec_principal.add(classe.id)
        else:
            proposer_ligne(classe, choisi, True, "Classe sans professeur principal")
    return propositions


def appliquer(db: Session, etablissement_id: str, lignes: list[dict]) -> int:
    """Applique les lignes retenues par l'A+ (issues de `proposer`). Revalide chaque ligne :
    classe de l'etablissement, enseignant sous contrat signe ; un seul principal par classe."""
    enseignants = enseignants_sous_contrat(db, etablissement_id)
    appliquees = 0
    for ligne in lignes:
        classe = db.get(Classe, ligne["classe_id"])
        if classe is None or classe.etablissement_id != etablissement_id or ligne["enseignant_utilisateur_id"] not in enseignants:
            continue
        affectation = (
            db.query(AffectationEnseignant)
            .filter(AffectationEnseignant.classe_id == classe.id, AffectationEnseignant.enseignant_id == ligne["enseignant_utilisateur_id"])
            .first()
        )
        if affectation is None:
            affectation = AffectationEnseignant(enseignant_id=ligne["enseignant_utilisateur_id"], classe_id=classe.id)
            db.add(affectation)
            appliquees += 1
        if ligne.get("principal"):
            deja_principal = (
                db.query(AffectationEnseignant)
                .filter(AffectationEnseignant.classe_id == classe.id, AffectationEnseignant.est_professeur_principal.is_(True))
                .first()
            )
            if deja_principal is None:
                affectation.est_professeur_principal = True
        db.flush()
    db.commit()
    return appliquees
