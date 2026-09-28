"""Lot 7.7 — centre d'alphabetisation (PAG, action 4 : alphabetisation et education des
adultes) : classes, cours courts a ecouter avec quiz oral, adultes inscrits sur leur propre
compte de parent. Le compte de demonstration « parent en mode Ecoute » en fait partie."""

from __future__ import annotations

from datetime import timedelta

from app.modules.alphabetisation.models import InscriptionAlphabetisation
from app.modules.etablissements.models import Classe, Etablissement
from app.modules.pedagogie.models import Cours, FormatCours, QuestionQuiz, Quiz

from .contexte import Contexte, new_id

NOM_CENTRE = "Centre d'alphabétisation de Bohicon"
NIVEAUX = {
    "Alphabétisation initiale": ["Lecture et écriture", "Calcul"],
    "Post-alphabétisation": ["Lecture et écriture", "Calcul", "Vie pratique"],
}

# (matiere, titre, contenu lu a voix haute, question, choix, bonne reponse)
LECONS = (
    ("Lecture et écriture", "Les voyelles", "Les voyelles sont A, E, I, O et U. On les entend dans maman, bébé, midi, moto et tutu.",
     "Quelle lettre est une voyelle ?", ["B", "A", "T"], 1),
    ("Lecture et écriture", "Écrire son prénom", "Votre prénom commence par une lettre majuscule. Recopiez-le chaque jour sur une ligne entière.",
     "Par quelle lettre commence un prénom ?", ["Une majuscule", "Un chiffre", "Un point"], 0),
    ("Calcul", "Compter l'argent du marché", "Deux pièces de cent francs font deux cents francs. Cinq pièces de cent francs font cinq cents francs.",
     "Deux pièces de cent francs, combien cela fait-il ?", ["Cent francs", "Deux cents francs", "Mille francs"], 1),
    ("Calcul", "Lire l'heure", "La petite aiguille montre l'heure, la grande aiguille montre les minutes.",
     "Quelle aiguille montre l'heure ?", ["La grande", "La petite"], 1),
    ("Vie pratique", "Lire un bulletin scolaire", "La moyenne est sur vingt. Dix sur vingt, c'est la moyenne. Au-dessus, c'est bien.",
     "Douze sur vingt, est-ce au-dessus de la moyenne ?", ["Oui", "Non"], 0),
)


def creer_centre(ctx: Contexte, etablissement, classe) -> Etablissement:
    """Appele par etablissements.creer_etablissements (memes regles que les autres types)."""
    from app.modules.etablissements.models import StatutEtablissement, TypeEtablissement

    etab = etablissement(ctx, NOM_CENTRE, TypeEtablissement.CA, StatutEtablissement.PUBLIC)
    for niveau, matieres in NIVEAUX.items():
        classe(ctx, etab, niveau, matieres)
    return etab


def peupler(ctx: Contexte, etab: Etablissement) -> None:
    classes: list[Classe] = ctx.classes_par_etab[etab.id]
    for classe in classes:
        auteurs = {a.enseignant.id: a.enseignant for a in ctx.affectations_par_classe[classe.id]}
        auteur = next(iter(auteurs.values()))
        publie = ctx.debut_activite + timedelta(days=3)
        for matiere, titre, contenu, enonce, choix, bonne in LECONS:
            if matiere not in ctx.matieres_par_classe[classe.id]:
                continue
            cours = Cours(
                id=new_id(), classe_id=classe.id, enseignant_id=auteur.id, titre=titre, chapitre=matiere,
                format=FormatCours.TEXTE, contenu_texte=contenu, created_at=publie,
            )
            ctx.ajouter(cours)
            quiz = Quiz(id=new_id(), cours_id=cours.id, seuil_reussite=50.0, created_at=publie + timedelta(hours=1))
            ctx.ajouter(quiz)
            ctx.ajouter(QuestionQuiz(id=new_id(), quiz_id=quiz.id, ordre=1, enonce=enonce, choix=choix, reponse_correcte_index=bonne))

    # Des parents deja presents sur la plateforme suivent les cours (un tiers de la capacite).
    # Le premier est le compte de demonstration « parent en mode Ecoute » : un parent dont
    # un enfant est scolarise, pour que l'accueil par images ait des nouvelles a donner.
    parents = {i.eleve.tuteur_id for liste in ctx.inscrits_par_etab.values() for i in liste if i.eleve.tuteur_id}
    tuteurs = list(ctx.tuteurs.values())
    ctx.rng.shuffle(tuteurs)
    tuteurs.sort(key=lambda t: t.id not in parents)
    demo = tuteurs[0]
    demo.preferences_accessibilite = {
        "taille": "grand", "contraste": False, "espacement": False, "animations_reduites": False,
        "donnees": "auto", "mode_ecoute": True, "langue_audio": "fr",
    }
    ctx.protege.update({demo.id, etab.id})  # jamais suspendus (comptes et centre de demonstration)
    ctx.demo["Parent en mode Écoute (apprend aussi à lire au centre)"] = demo.login_id
    ctx.demo["A+ centre d'alphabétisation"] = ctx.admin_par_etab[etab.id].login_id
    rang = 0
    for classe in classes:
        for _ in range(max(3, classe.capacite // 3)):
            if rang >= len(tuteurs):
                return
            ctx.ajouter(InscriptionAlphabetisation(
                id=new_id(), utilisateur_id=tuteurs[rang].id, classe_id=classe.id,
                created_at=ctx.debut_activite + timedelta(days=ctx.rng.randint(1, 20)),
            ))
            rang += 1
