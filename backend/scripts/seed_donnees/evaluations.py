"""Devoirs, soumissions, bulletins (UC-08/09/26) et vie scolaire (UC-23).

- un devoir est donne par un enseignant affecte a la classe, dans sa matiere ;
- une copie est deposee AVANT l'echeance ; corrigee (ou en echec de correction, en
  attente de revision manuelle) - jamais "en correction" indefiniment ;
- la note suit le niveau de l'eleve ;
- le bulletin du trimestre est CALCULE comme evaluations/router.py::_calculer_et_enregistrer_bulletin :
  devoirs SOMMATIFS uniquement, note normalisee sur 100, ponderee par le coefficient du
  referentiel, 0 pour une copie non rendue une fois l'echeance passee.
"""

from __future__ import annotations

from datetime import timedelta

from app.modules.etablissements.models import Classe
from app.modules.evaluations.models import (
    BaremeDevoir,
    Bulletin,
    Devoir,
    NatureEvaluation,
    QuestionDevoir,
    ReponseSoumission,
    Soumission,
    StatutSoumission,
)
from app.modules.vie_scolaire.models import EntreeVieScolaire, NatureEntreeVieScolaire

from .contexte import Contexte, new_id
from .taxonomie import notion_pour

PERIODE = "trimestre1"

ENONCES = [
    ("Rappelle la définition principale du chapitre et illustre-la par un exemple.", 6.0),
    ("Applique la méthode du cours à la situation suivante et justifie chaque étape.", 8.0),
    ("Rédige une courte synthèse (5 lignes) de ce que tu as retenu.", 6.0),
]
REPONSES = [
    "D'après le cours, la définition est la suivante ; par exemple, dans la situation vue en classe, on observe bien la propriété.",
    "J'applique la méthode : je pose les données, j'utilise la règle du cours puis je vérifie le résultat obtenu.",
    "Ce chapitre montre comment la notion s'applique dans la vie courante ; il faut retenir la règle et sa méthode.",
]


def creer_devoirs(ctx: Contexte, classe: Classe) -> list[Devoir]:
    inscrits = ctx.inscrits_par_classe[classe.id]
    notes_ponderees: dict[str, list[tuple[float, float]]] = {i.eleve.id: [] for i in inscrits}
    devoirs: list[Devoir] = []

    for rang in range(ctx.cfg.devoirs_par_classe):
        affectation = ctx.rng.choice(ctx.affectations_par_classe[classe.id])
        matieres = ctx.matieres_par_classe[classe.id]
        matiere = affectation.matiere if affectation.matiere in matieres else ctx.rng.choice(matieres)
        chapitre, _ = notion_pour(matiere)
        clos = rang < max(1, ctx.cfg.devoirs_par_classe - 1)  # le dernier est encore a rendre
        if clos:
            echeance = ctx.instant_scolaire(ctx.debut_activite + timedelta(days=7), ctx.maintenant - timedelta(days=1))
        else:
            echeance = ctx.instant_scolaire(ctx.maintenant + timedelta(days=3), ctx.maintenant + timedelta(days=20))
        # Donne entre 5 et 10 jours avant l'echeance, et toujours dans le passe.
        donne_le = min(max(echeance - timedelta(days=ctx.rng.randint(5, 10)), ctx.debut_activite), ctx.maintenant - timedelta(days=1))
        nature = NatureEvaluation.FORMATIVE if ctx.rng.random() < 0.2 else NatureEvaluation.SOMMATIVE
        devoir = Devoir(
            id=new_id(), classe_id=classe.id, enseignant_id=affectation.enseignant.id,
            titre=f"{'Interrogation' if nature == NatureEvaluation.FORMATIVE else 'Devoir surveillé'} n°{rang + 1} — {chapitre}",
            matiere=matiere, date_limite=echeance, bareme=ctx.rng.choice(list(BaremeDevoir)), nature=nature,
            sujet_lulufiles_file_id=ctx.fichiers.sujet_devoir(matiere, f"Sujet — {chapitre}", [e for e, _ in ENONCES]) if ctx.rng.random() < 0.5 else None,
            created_at=donne_le,
        )
        ctx.ajouter(devoir)
        devoirs.append(devoir)
        questions = []
        for ordre, (enonce, points) in enumerate(ENONCES, start=1):
            q = QuestionDevoir(
                id=new_id(), devoir_id=devoir.id, ordre=ordre, enonce=enonce, points_max=points,
                bareme_reponse=f"Réponse attendue : notions clés de « {chapitre} », raisonnement complet et justifié.",
            )
            ctx.ajouter(q)
            questions.append(q)
        points_max = sum(q.points_max for q in questions)
        coefficient = ctx.coefficients.get((classe.niveau, matiere), 1.0)

        for inscrit in inscrits:
            rend = ctx.rng.random() < (0.9 if clos else 0.25)
            if not rend:
                if clos and nature == NatureEvaluation.SOMMATIVE:
                    notes_ponderees[inscrit.eleve.id].append((0.0, coefficient))  # non rendu : 0 apres echeance
                continue
            fin_depot = min(echeance, ctx.maintenant) - timedelta(minutes=5)
            depose = ctx.instant(donne_le + timedelta(hours=1), fin_depot)
            echec = ctx.rng.random() < 0.06
            par_photo = ctx.rng.random() < 0.15
            photo = ctx.fichiers.copie(ctx.sequence("copie")) if par_photo else None
            par_photo = photo is not None
            soumission = Soumission(
                id=new_id(), devoir_id=devoir.id, eleve_id=inscrit.eleve.id,
                statut=StatutSoumission.ECHEC_CORRECTION if echec else StatutSoumission.CORRIGEE,
                copie_image_lulufiles_file_id=photo, created_at=depose,
            )
            ctx.ajouter(soumission)
            total = 0.0
            for q in questions:
                obtenu = round(min(q.points_max, max(0.0, ctx.rng.gauss(inscrit.niveau_scolaire, 0.12) * q.points_max)) * 2) / 2
                total += obtenu
                if not par_photo:
                    ctx.ajouter(ReponseSoumission(
                        id=new_id(), soumission_id=soumission.id, question_id=q.id,
                        texte_reponse=ctx.rng.choice(REPONSES),
                        points_obtenus=None if echec else obtenu,
                        commentaire_ia=None if echec else (
                            "Réponse complète et bien justifiée." if obtenu >= 0.75 * q.points_max
                            else "Réponse partielle : la justification manque de précision."
                        ),
                    ))
            if not echec:
                soumission.note = round(total, 1)
                if nature == NatureEvaluation.SOMMATIVE:
                    notes_ponderees[inscrit.eleve.id].append((soumission.note / points_max * 100, coefficient))

    for inscrit in inscrits:
        notes = notes_ponderees[inscrit.eleve.id]
        poids = sum(c for _, c in notes)
        if poids == 0:
            continue  # aucun devoir clos et evalue : pas de bulletin (l'ecran affiche un etat vide)
        ctx.ajouter(Bulletin(
            id=new_id(), eleve_id=inscrit.eleve.id, classe_id=classe.id, periode=PERIODE,
            moyenne_generale=sum(n * c for n, c in notes) / poids, valide_par_conseil=False,
            created_at=ctx.maintenant - timedelta(hours=ctx.rng.randint(1, 48)),
        ))
    return devoirs


VIE_SCOLAIRE = {
    NatureEntreeVieScolaire.ABSENCE: ["Absent(e) sans justificatif.", "Absence justifiée par un certificat médical."],
    NatureEntreeVieScolaire.RETARD: ["Arrivé(e) avec 15 minutes de retard.", "Retard en début de journée."],
    NatureEntreeVieScolaire.APPRECIATION: ["Participation active et pertinente.", "Travail régulier et soigné."],
    NatureEntreeVieScolaire.INCIDENT: ["Bavardages répétés malgré les rappels.", "Oubli de matériel pour la troisième fois."],
    NatureEntreeVieScolaire.FELICITATION: ["Excellents résultats au dernier devoir.", "Attitude exemplaire et entraide envers les camarades."],
}


def creer_vie_scolaire(ctx: Contexte, classe: Classe) -> None:
    """Entree globale (matiere NULL) : professeur principal uniquement ; un enseignant de
    matiere indique toujours la sienne. Les bons eleves recoivent surtout appreciations et
    felicitations, les plus fragiles davantage d'absences, retards et incidents."""
    affectations = ctx.affectations_par_classe[classe.id]
    for inscrit in ctx.inscrits_par_classe[classe.id]:
        if ctx.rng.random() >= 0.45:
            continue
        for _ in range(ctx.rng.randint(1, 3)):
            if inscrit.niveau_scolaire > 0.7:
                nature = ctx.rng.choice([NatureEntreeVieScolaire.APPRECIATION, NatureEntreeVieScolaire.FELICITATION, NatureEntreeVieScolaire.RETARD])
            elif inscrit.niveau_scolaire < 0.45:
                nature = ctx.rng.choice([NatureEntreeVieScolaire.ABSENCE, NatureEntreeVieScolaire.RETARD, NatureEntreeVieScolaire.INCIDENT, NatureEntreeVieScolaire.APPRECIATION])
            else:
                nature = ctx.rng.choice(list(NatureEntreeVieScolaire))
            affectation = ctx.rng.choice(affectations)
            globale = affectation.principal and (affectation.matiere is None or ctx.rng.random() < 0.5)
            matiere = None if globale else (
                affectation.matiere if affectation.matiere in ctx.matieres_par_classe[classe.id]
                else ctx.rng.choice(ctx.matieres_par_classe[classe.id])
            )
            survenue = ctx.instant_scolaire(ctx.debut_activite, ctx.maintenant - timedelta(hours=3))
            ctx.ajouter(EntreeVieScolaire(
                id=new_id(), eleve_id=inscrit.eleve.id, classe_id=classe.id, auteur_id=affectation.enseignant.id,
                nature=nature, matiere=matiere, description=ctx.rng.choice(VIE_SCOLAIRE[nature]),
                date_survenue=survenue.date(), created_at=survenue + timedelta(hours=1),
            ))
