"""Pedagogie (UC-06/07/14) et El Professor (4 personas).

Chaque cours est publie par un enseignant AFFECTE a la classe, dans sa matiere quand il en
a une ; un cours PDF porte un vrai fichier et son texte extrait (ce que lisent El Professor
et la generation de quiz). Les tentatives de quiz suivent le niveau de l'eleve.
"""

from __future__ import annotations

from datetime import timedelta

from app.modules.etablissements.models import Classe
from app.modules.pedagogie.models import (
    AlerteElProfessor,
    Cours,
    FormatCours,
    MessageElProfessor,
    MessageElProfessorEnseignant,
    MessageElProfessorFamille,
    MessageElProfessorTuteur,
    OrigineAlerteElProfessor,
    QuestionQuiz,
    Quiz,
    RoleMessageElProfessor,
    RoleMessageElProfessorEnseignant,
    RoleMessageElProfessorFamille,
    RoleMessageElProfessorTuteur,
    SessionElProfessor,
    SessionElProfessorEnseignant,
    SessionElProfessorFamille,
    SessionElProfessorTuteur,
    TentativeQuiz,
)

from .contexte import Contexte, EleveInscrit, new_id
from .taxonomie import notion_pour

SEUIL_QUIZ = 80.0


def _auteur_et_matiere(ctx: Contexte, classe: Classe):
    affectation = ctx.rng.choice(ctx.affectations_par_classe[classe.id])
    matieres = ctx.matieres_par_classe[classe.id]
    matiere = affectation.matiere if affectation.matiere in matieres else ctx.rng.choice(matieres)
    return affectation.enseignant, matiere


def _questions_quiz(titre: str, contenu: str) -> list[tuple[str, list[str], int]]:
    phrases = [p.strip() for p in contenu.replace(" ; ", ". ").split(". ") if len(p.strip()) > 25]
    questions = []
    for i, phrase in enumerate(phrases[:4]):
        correcte = phrase.rstrip(".") + "."
        choix = [
            correcte,
            "Cette notion ne s'applique que dans des cas exceptionnels, sans règle générale.",
            "Le cours affirme exactement le contraire de cette idée.",
            "Aucune des propositions ne correspond au cours.",
        ]
        rang = i % 4
        choix[0], choix[rang] = choix[rang], choix[0]
        questions.append((f"Selon le cours « {titre} », quelle affirmation est exacte ?", choix, rang))
    return questions


def creer_cours(ctx: Contexte, classe: Classe) -> list[Cours]:
    inscrits = ctx.inscrits_par_classe[classe.id]
    cours_crees = []
    for _ in range(ctx.cfg.cours_par_classe):
        enseignant, matiere = _auteur_et_matiere(ctx, classe)
        chapitre, contenu = notion_pour(matiere)
        publie = ctx.instant_scolaire(ctx.debut_activite, ctx.maintenant - timedelta(days=1))
        format_cours = FormatCours.TEXTE
        fichier = None
        tirage = ctx.rng.random()
        if tirage < 0.4:
            fichier = ctx.fichiers.cours_pdf(matiere, chapitre, contenu, classe.niveau)
            format_cours = FormatCours.PDF if fichier else FormatCours.TEXTE
        elif tirage < 0.45:
            fichier = ctx.fichiers.cours_audio()
            format_cours = FormatCours.AUDIO if fichier else FormatCours.TEXTE
        cours = Cours(
            id=new_id(), classe_id=classe.id, enseignant_id=enseignant.id, titre=f"{matiere} — {chapitre}",
            chapitre=chapitre, format=format_cours, lulufiles_file_id=fichier,
            contenu_texte=contenu if format_cours == FormatCours.TEXTE else None,
            texte_extrait=contenu if format_cours == FormatCours.PDF else None,
            # Lot 7.3 : tout cours oral publie porte sa transcription.
            transcription=contenu if format_cours == FormatCours.AUDIO else None,
            created_at=publie,
        )
        ctx.ajouter(cours)
        cours_crees.append(cours)

        texte = cours.contenu_texte or cours.texte_extrait
        questions = _questions_quiz(chapitre, texte) if texte else []
        if len(questions) >= 2 and ctx.rng.random() < 0.7:
            quiz = Quiz(id=new_id(), cours_id=cours.id, seuil_reussite=SEUIL_QUIZ, created_at=publie + timedelta(hours=1))
            ctx.ajouter(quiz)
            bonnes = []
            for ordre, (enonce, choix, bonne) in enumerate(questions, start=1):
                ctx.ajouter(QuestionQuiz(id=new_id(), quiz_id=quiz.id, ordre=ordre, enonce=enonce, choix=choix, reponse_correcte_index=bonne))
                bonnes.append(bonne)
            for inscrit in inscrits:
                if ctx.rng.random() < 0.55:
                    _tentatives(ctx, quiz, bonnes, inscrit, publie)
        if inscrits and ctx.rng.random() < 0.35:
            _el_professor_cours(ctx, ctx.rng.choice(inscrits), cours, chapitre, publie)
    return cours_crees


def _tentatives(ctx: Contexte, quiz: Quiz, bonnes: list[int], inscrit: EleveInscrit, publie) -> None:
    moment = ctx.instant(publie + timedelta(hours=2), ctx.maintenant)
    for essai in range(1 if ctx.rng.random() < 0.7 else 2):
        aptitude = min(0.99, inscrit.niveau_scolaire + 0.12 * essai)
        reponses = [b if ctx.rng.random() < aptitude else (b + 1) % 4 for b in bonnes]
        score = round(100 * sum(r == b for r, b in zip(reponses, bonnes)) / len(bonnes), 1)
        ctx.ajouter(TentativeQuiz(
            id=new_id(), quiz_id=quiz.id, eleve_id=inscrit.eleve.id, reponses=reponses, score=score,
            reussie=score >= SEUIL_QUIZ, created_at=moment,
        ))
        if score >= SEUIL_QUIZ:
            break
        moment = moment + timedelta(hours=ctx.rng.randint(1, 30))
        if moment > ctx.maintenant:
            break


def _messages(ctx: Contexte, modele, session_id: str, tours: list[tuple[object, str]], debut) -> None:
    moment = debut
    for role, contenu in tours:
        ctx.ajouter(modele(id=new_id(), session_id=session_id, role=role, contenu=contenu, created_at=moment))
        moment = moment + timedelta(seconds=ctx.rng.randint(8, 240))


def _el_professor_cours(ctx: Contexte, inscrit: EleveInscrit, cours: Cours, chapitre: str, publie) -> None:
    debut = ctx.instant(publie + timedelta(hours=3), ctx.maintenant)
    session = SessionElProfessor(
        id=new_id(), eleve_utilisateur_id=inscrit.utilisateur.id, cours_id=cours.id, created_at=debut
    )
    ctx.ajouter(session)
    _messages(ctx, MessageElProfessor, session.id, [
        (RoleMessageElProfessor.ELEVE, f"Je n'ai pas bien compris « {chapitre} ». Tu peux m'expliquer autrement ?"),
        (RoleMessageElProfessor.ASSISTANT, f"Bien sûr ! Reprenons **{chapitre}** pas à pas.\n\n1. Commence par repérer la définition clé du cours.\n2. Applique-la sur l'exemple du cours, ligne par ligne.\n3. Essaie ensuite un cas proche par toi-même.\n\nDis-moi à quelle étape tu bloques et on la détaille ensemble."),
        (RoleMessageElProfessor.ELEVE, "C'est l'étape 2 qui me pose problème."),
        (RoleMessageElProfessor.ASSISTANT, "D'accord. Écris-moi ce que tu obtiens après la première ligne de l'exemple : je te dirai si tu es sur la bonne voie, sans te donner la réponse toute faite."),
    ], debut)


QUESTIONS_GENERALES = [
    ("Organisation", "Comment organiser mes révisions pour les devoirs de la semaine prochaine ?",
     "Voici un plan simple :\n\n- **Lundi et mardi** : relis tes cours et fais une fiche par chapitre.\n- **Mercredi** : entraîne-toi sur deux exercices par matière.\n- **Jeudi** : refais les exercices ratés.\n\nCourtes séances de 45 minutes, avec une pause entre chaque."),
    ("Méthode", "Comment bien apprendre une leçon par cœur ?",
     "Lis la leçon une première fois en entier, puis cache-la et essaie de réciter les idées principales. Reviens sur ce que tu as oublié. Refais l'exercice le lendemain : la répétition espacée est la méthode la plus efficace."),
    ("Orientation", "Quelle série choisir après la 3ème si j'aime les sciences ?",
     "Si tu aimes les mathématiques et la physique, la **série C** est adaptée ; si tu préfères la biologie, la **série D**. Parles-en aussi avec ton professeur principal et tes parents : tes résultats de l'année compteront."),
]


def el_professor_eleves(ctx: Contexte, inscrits: list[EleveInscrit]) -> None:
    """Conversations d'aide generale (hors d'un cours) et, rarement, un signal de detresse
    ayant prepare une alerte pour l'administration (origine ELEVE, jamais montree au tuteur)."""
    for inscrit in inscrits:
        if ctx.rng.random() >= 0.12:
            continue
        sujet, question, reponse = ctx.rng.choice(QUESTIONS_GENERALES)
        debut = ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=1))
        session = SessionElProfessor(
            id=new_id(), eleve_utilisateur_id=inscrit.utilisateur.id, cours_id=None, sujet=sujet, created_at=debut
        )
        ctx.ajouter(session)
        _messages(ctx, MessageElProfessor, session.id, [
            (RoleMessageElProfessor.ELEVE, question), (RoleMessageElProfessor.ASSISTANT, reponse),
        ], debut)
        if ctx.rng.random() < 0.06:
            moment = debut + timedelta(minutes=10)
            motif = "Je suis triste, on me frappe quand je rentre à la maison."
            _messages(ctx, MessageElProfessor, session.id, [
                (RoleMessageElProfessor.ELEVE, motif),
                (RoleMessageElProfessor.ASSISTANT, "Ce n'est pas de ta faute, et tu mérites d'être en sécurité. Parles-en aujourd'hui même à un adulte de confiance ou à l'administration de ton établissement.\n\n💛 Si tu vis quelque chose de difficile, tu n'es pas seul·e : parles-en dès que possible à un adulte de confiance (un parent, un enseignant, l'administration de ton établissement). En cas de danger immédiat, va vers l'adulte le plus proche ou appelle la police. L'équipe de ton établissement a été prévenue pour pouvoir t'aider."),
            ], moment)
            _alerte(ctx, OrigineAlerteElProfessor.ELEVE, session.id, inscrit, motif, moment)


def _alerte(ctx: Contexte, origine, session_id: str, inscrit: EleveInscrit, motif: str, moment) -> None:
    traitee = ctx.rng.random() < 0.4 and moment < ctx.maintenant - timedelta(days=1)
    ctx.ajouter(AlerteElProfessor(
        id=new_id(), origine=origine, session_id=session_id, etablissement_id=inscrit.etablissement.id,
        eleve_utilisateur_id=inscrit.utilisateur.id, motif=motif, traite=traitee,
        traite_par_id=ctx.admin_par_etab[inscrit.etablissement.id].id if traitee else None, created_at=moment,
    ))


def el_professor_enseignants(ctx: Contexte, classe: Classe) -> None:
    inscrits = ctx.inscrits_par_classe[classe.id]
    for affectation in ctx.affectations_par_classe[classe.id]:
        if ctx.rng.random() >= 0.25:
            continue
        inscrit = ctx.rng.choice(inscrits) if inscrits and ctx.rng.random() < 0.6 else None
        debut = ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=2))
        session = SessionElProfessorEnseignant(
            id=new_id(), enseignant_id=affectation.enseignant.id,
            eleve_utilisateur_id=inscrit.utilisateur.id if inscrit else None,
            sujet=f"Suivi de {inscrit.eleve.prenom}" if inscrit else "Préparation de séquence", created_at=debut,
        )
        ctx.ajouter(session)
        if inscrit:
            tours = [
                (RoleMessageElProfessorEnseignant.ENSEIGNANT, f"{inscrit.eleve.prenom} décroche depuis deux semaines en {classe.niveau}. Comment réagir ?"),
                (RoleMessageElProfessorEnseignant.ASSISTANT, "Commencez par un échange individuel, sans reproche, pour comprendre ce qui a changé. Proposez un objectif court et atteignable, valorisez le moindre progrès et associez la famille si la situation persiste."),
            ]
        else:
            tours = [
                (RoleMessageElProfessorEnseignant.ENSEIGNANT, "Propose-moi une séquence de quatre séances pour introduire un nouveau chapitre."),
                (RoleMessageElProfessorEnseignant.ASSISTANT, "1. **Découverte** : situation-problème concrète.\n2. **Institutionnalisation** : la notion et sa définition.\n3. **Entraînement** : exercices gradués.\n4. **Évaluation formative** : un court quiz pour vérifier les acquis."),
            ]
        _messages(ctx, MessageElProfessorEnseignant, session.id, tours, debut)
        if inscrit and ctx.rng.random() < 0.05:
            motif = f"Je pense que {inscrit.eleve.prenom} subit des violences à la maison, il arrive avec des marques."
            moment = debut + timedelta(minutes=15)
            _messages(ctx, MessageElProfessorEnseignant, session.id, [
                (RoleMessageElProfessorEnseignant.ENSEIGNANT, motif),
                (RoleMessageElProfessorEnseignant.ASSISTANT, "Ne restez pas seul avec cette inquiétude : notez les faits observés, sans interroger l'élève comme un enquêteur, et signalez-les aujourd'hui à la direction.\n\n⚠️ Cette situation semble sensible : parlez-en sans délai à l'administration de l'établissement (ou aux autorités compétentes si l'urgence l'exige). Une alerte a été préparée pour l'administration."),
            ], moment)
            _alerte(ctx, OrigineAlerteElProfessor.ENSEIGNANT, session.id, inscrit, motif, moment)


def el_professor_familles(ctx: Contexte, inscrit: EleveInscrit) -> None:
    """Conseil au tuteur (toujours a propos d'un de SES enfants) et fil familial partage,
    ecrit seulement une fois rejoint par l'enfant."""
    tuteur_id = inscrit.eleve.tuteur_id
    if ctx.rng.random() < 0.12:
        debut = ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=1))
        session = SessionElProfessorTuteur(
            id=new_id(), tuteur_id=tuteur_id, eleve_utilisateur_id=inscrit.utilisateur.id,
            sujet="Motivation et devoirs", created_at=debut,
        )
        ctx.ajouter(session)
        _messages(ctx, MessageElProfessorTuteur, session.id, [
            (RoleMessageElProfessorTuteur.TUTEUR, f"Comment aider {inscrit.eleve.prenom} à mieux s'organiser pour ses devoirs ?"),
            (RoleMessageElProfessorTuteur.ASSISTANT, f"Fixez avec {inscrit.eleve.prenom} un moment régulier et calme pour les devoirs, vérifiez ensemble l'agenda chaque soir, et encouragez l'effort plutôt que la seule note. Un point hebdomadaire de dix minutes suffit souvent à installer une routine."),
        ], debut)
    if ctx.rng.random() < 0.08:
        debut = ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=1))
        rejointe = ctx.rng.random() < 0.7
        session = SessionElProfessorFamille(
            id=new_id(), tuteur_id=tuteur_id, eleve_utilisateur_id=inscrit.utilisateur.id,
            sujet="Objectifs du trimestre", created_at=debut,
            rejointe_le=min(debut + timedelta(hours=ctx.rng.randint(1, 30)), ctx.maintenant - timedelta(minutes=30)) if rejointe else None,
        )
        ctx.ajouter(session)
        if rejointe:
            _messages(ctx, MessageElProfessorFamille, session.id, [
                (RoleMessageElProfessorFamille.TUTEUR, "Fixons ensemble des objectifs pour ce trimestre."),
                (RoleMessageElProfessorFamille.ELEVE, "Je voudrais progresser en mathématiques."),
                (RoleMessageElProfessorFamille.ASSISTANT, f"Excellente idée ! De ton côté, {inscrit.eleve.prenom}, choisis deux chapitres à retravailler. Pour vous, côté parent, un point rapide chaque dimanche aidera à suivre les progrès sans pression."),
            ], session.rejointe_le)

