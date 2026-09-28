"""Lot 7.4 — mode Ecoute : ce qu'un parent doit savoir sur chaque enfant, en phrases
courtes destinees a etre LUES A VOIX HAUTE (personnes qui ne lisent pas ou peu).

Phrases construites sans IA, a partir des donnees : un parent qui ne peut pas relire
l'ecran doit pouvoir faire confiance a ce qu'il entend. Aucune ecriture en base (le
bulletin est recalcule sans etre enregistre).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.coffre_fort.models import StatutValidationParentale, ValidationParentale
from app.modules.etablissements.models import Classe, Etablissement
from app.modules.evaluations import periodes as periodes_evaluation
from app.modules.evaluations.decisions import libelle_decision
from app.modules.evaluations.models import Bulletin, Devoir, Soumission
from app.modules.evaluations.router import notes_de_la_periode
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.vie_scolaire.models import EntreeVieScolaire, NatureEntreeVieScolaire


@dataclass
class Tuile:
    cle: str  # pictogramme et fichier audio pre-enregistre du titre (bulletin, presences...)
    titre: str
    phrase: str
    lien: str
    alerte: bool = False  # quelque chose attend le parent
    # Inscription dont le consentement parental peut etre donne directement depuis la tuile.
    consentement_inscription_id: str | None = None


@dataclass
class EnfantEcoute:
    eleve_utilisateur_id: str | None
    prenom: str
    tuiles: list[Tuile] = field(default_factory=list)


def _sur_20(moyenne_sur_100: float) -> str:
    valeur = round(moyenne_sur_100 / 5, 1)
    texte = f"{valeur:.1f}".replace(".0", "").replace(".", ",")
    return f"{texte} sur 20"


def _classe_actuelle(db: Session, eleve: Eleve) -> Classe | None:
    inscription = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )
    return db.get(Classe, inscription.classe_id) if inscription else None


def _tuile_bulletin(db: Session, eleve: Eleve, classe: Classe, lien: str) -> Tuile:
    etablissement = db.get(Etablissement, classe.etablissement_id)
    periode = periodes_evaluation.periode_de(datetime.now(timezone.utc), etablissement.type, classe.annee_academique)
    decide = (
        db.query(Bulletin)
        .filter(Bulletin.eleve_id == eleve.id, Bulletin.classe_id == classe.id, Bulletin.valide_par_conseil.is_(True))
        .order_by(Bulletin.updated_at.desc())
        .first()
    )
    phrases = []
    notes = notes_de_la_periode(db, eleve, classe.id, periode.code)
    poids = sum(c for _, _, c in notes)
    moyenne: float | None = None
    if poids:
        moyenne = sum(n * c for _, n, c in notes) / poids
        appreciation = "C'est au-dessus de la moyenne." if moyenne >= 50 else "C'est en dessous de la moyenne : il faut l'encourager."
        phrases.append(f"Pour le {periode.libelle}, {eleve.prenom} a {_sur_20(moyenne)} de moyenne. {appreciation}")
    else:
        phrases.append(f"Pour le {periode.libelle}, {eleve.prenom} n'a pas encore de note.")
    if decide is not None and decide.decision_passage:
        phrases.append(f"Le conseil de classe a décidé : {libelle_decision(decide.decision_passage)}.")
    return Tuile("bulletin", "Bulletin", " ".join(phrases), lien, alerte=moyenne is not None and moyenne < 50)


def _tuile_presences(db: Session, eleve: Eleve, lien: str) -> Tuile:
    depuis = date.today() - timedelta(days=30)
    compte = dict(
        db.query(EntreeVieScolaire.nature, func.count(EntreeVieScolaire.id))
        .filter(EntreeVieScolaire.eleve_id == eleve.id, EntreeVieScolaire.date_survenue >= depuis)
        .group_by(EntreeVieScolaire.nature)
        .all()
    )
    absences = compte.get(NatureEntreeVieScolaire.ABSENCE, 0)
    retards = compte.get(NatureEntreeVieScolaire.RETARD, 0)
    felicitations = compte.get(NatureEntreeVieScolaire.FELICITATION, 0)
    incidents = compte.get(NatureEntreeVieScolaire.INCIDENT, 0)
    if not absences and not retards:
        phrase = f"Ce mois-ci, {eleve.prenom} n'a manqué aucun cours et n'a jamais été en retard."
    else:
        morceaux = []
        if absences:
            morceaux.append(f"{absences} absence{'s' if absences > 1 else ''}")
        if retards:
            morceaux.append(f"{retards} retard{'s' if retards > 1 else ''}")
        phrase = f"Ce mois-ci, on compte {' et '.join(morceaux)} pour {eleve.prenom}."
    if felicitations:
        phrase += f" Ses professeurs ont écrit {felicitations} félicitation{'s' if felicitations > 1 else ''}."
    if incidents:
        phrase += f" Il y a eu {incidents} incident{'s' if incidents > 1 else ''} : allez voir l'école ou appelez le professeur."
    return Tuile("presences", "Présences", phrase, lien, alerte=absences + retards + incidents > 0)


def _tuile_devoirs(db: Session, eleve: Eleve, classe: Classe, lien: str) -> Tuile:
    rendus = db.query(Soumission.devoir_id).filter(Soumission.eleve_id == eleve.id)
    a_rendre = (
        db.query(func.count(Devoir.id))
        .filter(
            Devoir.classe_id == classe.id,
            Devoir.date_limite > datetime.now(timezone.utc),
            Devoir.masque_le.is_(None),
            Devoir.id.notin_(rendus),
        )
        .scalar()
        or 0
    )
    if a_rendre:
        phrase = f"{eleve.prenom} a {a_rendre} devoir{'s' if a_rendre > 1 else ''} à rendre bientôt."
    else:
        phrase = f"{eleve.prenom} a rendu tous ses devoirs."
    return Tuile("devoirs", "Devoirs", phrase, lien, alerte=a_rendre > 0)


def _tuile_accords(db: Session, tuteur_id: str, eleve: Eleve, lien: str) -> Tuile | None:
    depenses = (
        db.query(func.count(ValidationParentale.id))
        .filter(
            ValidationParentale.tuteur_id == tuteur_id,
            ValidationParentale.eleve_utilisateur_id == eleve.utilisateur_id,
            ValidationParentale.statut == StatutValidationParentale.EN_ATTENTE,
        )
        .scalar()
        or 0
    )
    if not depenses:
        return None
    return Tuile(
        "paiements",
        "Argent",
        f"{eleve.prenom} veut faire {depenses} dépense{'s' if depenses > 1 else ''} qui attend{'ent' if depenses > 1 else ''} votre accord.",
        lien,
        alerte=True,
    )


def resume_oral_tuteur(db: Session, tuteur_id: str) -> list[EnfantEcoute]:
    enfants: list[EnfantEcoute] = []
    for eleve in db.query(Eleve).filter(Eleve.tuteur_id == tuteur_id).order_by(Eleve.prenom).all():
        enfant = EnfantEcoute(eleve_utilisateur_id=eleve.utilisateur_id, prenom=eleve.prenom)
        en_attente = (
            db.query(Inscription)
            .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL)
            .first()
        )
        if en_attente is not None:
            enfant.tuiles.append(
                Tuile(
                    "accord",
                    "Inscription",
                    f"L'inscription de {eleve.prenom} attend votre accord. Touchez le bouton vert pour donner votre accord.",
                    "/tuteur",
                    alerte=True,
                    consentement_inscription_id=en_attente.id,
                )
            )
        classe = _classe_actuelle(db, eleve)
        if classe is not None and eleve.utilisateur_id:
            suffixe = f"?enfant={eleve.utilisateur_id}"
            enfant.tuiles.append(_tuile_bulletin(db, eleve, classe, f"/tuteur/bulletins{suffixe}"))
            enfant.tuiles.append(_tuile_presences(db, eleve, f"/tuteur/vie-scolaire{suffixe}"))
            enfant.tuiles.append(_tuile_devoirs(db, eleve, classe, f"/tuteur/devoirs{suffixe}"))
            accords = _tuile_accords(db, tuteur_id, eleve, "/tuteur/coffre-fort")
            if accords is not None:
                enfant.tuiles.append(accords)
        elif en_attente is None:
            enfant.tuiles.append(
                Tuile("accord", "Inscription", f"{eleve.prenom} n'a pas encore de classe.", "/tuteur")
            )
        enfants.append(enfant)
    return enfants
