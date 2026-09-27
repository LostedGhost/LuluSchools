"""Messagerie (UC-13) et cours en direct (UC-16/25/33).

Messagerie, regles de messagerie/router.py : le groupe de classe reunit eleves et
enseignants affectes ; DM autorises : tuteur <-> SON enfant, eleve <-> eleve du MEME
etablissement, adulte <-> adulte (jamais un adulte du personnel avec un eleve).

Sessions en direct : PLANIFIEE a venir ou TERMINEE (jamais "en cours" a vie). Seule une
session terminee a des participants, un tableau (coordonnees normalisees 0-1, comme le
client), une capture PNG rendue par le vrai moteur (cours_direct/rendu_tableau.py) et
un resume.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.cours_direct.models import (
    CaptureTableauSession,
    DemandeCraie,
    MessageSessionLive,
    ModePermissionEcriture,
    PanneauTableau,
    ParticipationLive,
    PermissionEcritureTableau,
    ResumeSessionLive,
    SessionLive,
    StatutDemandeCraie,
    StatutSessionLive,
    TraitTableau,
    TypeTraitTableau,
)
from app.modules.cours_direct.rendu_tableau import rendre_panneau_png
from app.modules.etablissements.models import Classe, Etablissement
from app.modules.messagerie.models import Conversation, Message, ParticipantConversation, SignalementMessage, TypeConversation

from .contexte import Contexte, EleveInscrit, new_id

MESSAGES_GROUPE = [
    "Bonjour à tous, n'oubliez pas le devoir à rendre cette semaine.",
    "Quelqu'un peut me rappeler les pages à lire pour demain ?",
    "Merci pour la séance d'aujourd'hui, c'était très clair.",
    "Je serai absent(e) demain : quelqu'un pourra me passer les notes ?",
    "Rappel : réunion avec les parents vendredi à 17 h.",
    "Bon courage à tous pour les révisions !",
    "Les corrigés sont disponibles, pensez à les consulter.",
]
MESSAGES_FAMILLE = [
    ("Bonjour, comment s'est passée ta journée ?", "Bien, on a eu un contrôle ce matin."),
    ("N'oublie pas ton matériel de sport demain.", "D'accord, je le prépare ce soir."),
    ("Bravo pour ton dernier devoir !", "Merci, j'ai beaucoup révisé."),
    ("Je viendrai te chercher plus tard aujourd'hui.", "Pas de souci, je t'attends à la bibliothèque."),
]
MESSAGES_CAMARADES = [
    ("Tu as compris l'exercice 3 ?", "Oui, il faut appliquer la méthode vue mardi."),
    ("On révise ensemble samedi ?", "Avec plaisir, à la bibliothèque à 10 h ?"),
]


def _message(ctx: Contexte, conversation_id: str, auteur_id: str, contenu: str, moment: datetime) -> Message:
    return ctx.ajouter(Message(id=new_id(), conversation_id=conversation_id, auteur_id=auteur_id, contenu=contenu, created_at=moment))


def _dm(ctx: Contexte, a, b, echanges: list[tuple[str, str]]) -> None:
    conversation = Conversation(id=new_id(), type=TypeConversation.DM, classe_id=None,
                                created_at=ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(days=1)))
    ctx.ajouter(conversation)
    ctx.ajouter(ParticipantConversation(conversation_id=conversation.id, utilisateur_id=a.id))
    ctx.ajouter(ParticipantConversation(conversation_id=conversation.id, utilisateur_id=b.id))
    moment = conversation.created_at
    for question, reponse in echanges:
        _message(ctx, conversation.id, a.id, question, moment)
        moment += timedelta(minutes=ctx.rng.randint(2, 180))
        _message(ctx, conversation.id, b.id, reponse, min(moment, ctx.maintenant))
        moment += timedelta(hours=ctx.rng.randint(5, 48))
        if moment > ctx.maintenant:
            break


def messagerie_classe(ctx: Contexte, etab: Etablissement, classe: Classe, conversation_id: str) -> None:
    inscrits = ctx.inscrits_par_classe[classe.id]
    membres = [i.utilisateur for i in inscrits] + [a.enseignant for a in ctx.affectations_par_classe[classe.id]]
    if len(membres) < 2:
        return
    messages = []
    for _ in range(ctx.rng.randint(4, 10)):
        auteur = ctx.rng.choice(membres)
        messages.append(_message(ctx, conversation_id, auteur.id, ctx.rng.choice(MESSAGES_GROUPE),
                                 ctx.instant_scolaire(ctx.debut_activite, ctx.maintenant - timedelta(hours=1))))
    if ctx.rng.random() < 0.15:
        signale = ctx.rng.choice(messages)
        signaleur = ctx.rng.choice([m for m in membres if m.id != signale.auteur_id] or membres)
        traite = ctx.rng.random() < 0.6
        ctx.ajouter(SignalementMessage(
            id=new_id(), message_id=signale.id, signale_par_id=signaleur.id, traite=traite,
            decision="Message examiné : rappel des règles de courtoisie adressé à l'auteur." if traite else None,
            traite_par_id=ctx.admin_par_etab[etab.id].id if traite else None,
            created_at=signale.created_at + timedelta(hours=2),
        ))

    for inscrit in inscrits:
        if ctx.rng.random() < 0.35:
            tuteur = ctx.tuteurs[inscrit.eleve.tuteur_id]
            _dm(ctx, tuteur, inscrit.utilisateur, ctx.rng.sample(MESSAGES_FAMILLE, k=2))
    if len(inscrits) >= 2 and ctx.rng.random() < 0.5:
        a, b = ctx.rng.sample(inscrits, k=2)
        _dm(ctx, a.utilisateur, b.utilisateur, [ctx.rng.choice(MESSAGES_CAMARADES)])
    if inscrits and ctx.rng.random() < 0.25:
        # Adulte <-> adulte : le professeur principal ecrit au tuteur d'un eleve.
        principal = next(a.enseignant for a in ctx.affectations_par_classe[classe.id] if a.principal)
        inscrit = ctx.rng.choice(inscrits)
        _dm(ctx, principal, ctx.tuteurs[inscrit.eleve.tuteur_id], [(
            f"Bonjour, je souhaiterais faire le point avec vous sur le travail de {inscrit.eleve.prenom}.",
            "Bonjour, avec plaisir. Je suis disponible jeudi après 16 h.",
        )])


def _traits(ctx: Contexte) -> list[tuple[TypeTraitTableau, dict]]:
    traits = []
    for _ in range(ctx.rng.randint(3, 7)):
        if ctx.rng.random() < 0.6:
            x0, y0 = ctx.rng.uniform(0.1, 0.7), ctx.rng.uniform(0.2, 0.8)
            points = [[round(x0 + k * 0.03, 3), round(y0 + ctx.rng.uniform(-0.05, 0.05), 3)] for k in range(8)]
            traits.append((TypeTraitTableau.TRAIT_LIBRE, {"points": points, "couleur": ctx.rng.choice(["#FFFFFF", "#FDE047", "#93C5FD"]), "epaisseur": 0.006}))
        else:
            traits.append((TypeTraitTableau.TEXTE, {
                "x": round(ctx.rng.uniform(0.05, 0.6), 3), "y": round(ctx.rng.uniform(0.1, 0.9), 3),
                "texte": ctx.rng.choice(["Définition à retenir", "Exemple 1", "Méthode : 3 étapes", "Exercice 2 p. 45"]),
                "couleur": "#FFFFFF", "taille": 0.045,
            }))
    return traits


def sessions_live(ctx: Contexte, classe: Classe) -> None:
    inscrits = ctx.inscrits_par_classe[classe.id]
    for _ in range(ctx.cfg.sessions_live_par_classe):
        affectation = ctx.rng.choice(ctx.affectations_par_classe[classe.id])
        terminee = ctx.rng.random() < 0.6
        if terminee:
            debut = ctx.instant_scolaire(ctx.debut_activite, ctx.maintenant - timedelta(days=1))
        else:
            debut = ctx.instant_scolaire(ctx.maintenant + timedelta(days=1), ctx.maintenant + timedelta(days=21))
        session = SessionLive(
            id=new_id(), classe_id=classe.id, enseignant_id=affectation.enseignant.id, date_heure=debut,
            statut=StatutSessionLive.TERMINEE if terminee else StatutSessionLive.PLANIFIEE,
            created_at=min(debut, ctx.maintenant) - timedelta(days=ctx.rng.randint(2, 7)),
        )
        ctx.ajouter(session)
        if not terminee or not inscrits:
            continue
        participants: list[EleveInscrit] = ctx.rng.sample(inscrits, k=max(1, round(len(inscrits) * ctx.rng.uniform(0.4, 0.9))))
        for p in participants:
            ctx.ajouter(ParticipationLive(
                id=new_id(), session_id=session.id, eleve_utilisateur_id=p.utilisateur.id, camera_autorisee=p.camera,
                created_at=debut + timedelta(minutes=ctx.rng.randint(0, 10)),
            ))
        panneau = PanneauTableau(id=new_id(), session_id=session.id, ordre=0, created_at=debut)
        ctx.ajouter(panneau)
        objets_traits = []
        for k, (type_trait, donnees) in enumerate(_traits(ctx)):
            auteur = affectation.enseignant
            objets_traits.append(ctx.ajouter(TraitTableau(
                id=new_id(), panneau_id=panneau.id, auteur_id=auteur.id, type=type_trait, donnees=donnees,
                created_at=debut + timedelta(minutes=5 + k * 3),
            )))
        # Craie : une demande accordee donne une permission d'ecriture, les autres restent
        # refusees ou en attente (la session est terminee : plus rien a accorder).
        for k, p in enumerate(ctx.rng.sample(participants, k=min(2, len(participants)))):
            accordee = k == 0
            ctx.ajouter(DemandeCraie(
                id=new_id(), session_id=session.id, eleve_utilisateur_id=p.utilisateur.id,
                statut=StatutDemandeCraie.ACCORDEE if accordee else StatutDemandeCraie.REFUSEE,
                created_at=debut + timedelta(minutes=20 + k),
            ))
            if accordee:
                ctx.ajouter(PermissionEcritureTableau(
                    id=new_id(), session_id=session.id, eleve_utilisateur_id=p.utilisateur.id,
                    mode=ModePermissionEcriture.ACCORDEE, accordee_par_id=affectation.enseignant.id,
                    created_at=debut + timedelta(minutes=21),
                ))
        chat = [affectation.enseignant] + [p.utilisateur for p in participants]
        for k, texte in enumerate([
            "Bonjour à tous, on commence dans deux minutes.",
            "Je n'ai pas bien compris la deuxième étape, vous pouvez répéter ?",
            "Bien sûr : reprenons l'exemple au tableau.",
            "Merci, c'est plus clair maintenant !",
        ]):
            auteur = affectation.enseignant if k in (0, 2) else ctx.rng.choice(chat[1:] or chat)
            ctx.ajouter(MessageSessionLive(id=new_id(), session_id=session.id, auteur_id=auteur.id, contenu=texte,
                                           created_at=debut + timedelta(minutes=2 + k * 6)))
        capture = ctx.fichiers.capture_tableau(session.id, rendre_panneau_png(objets_traits)) if ctx.rng.random() < 0.12 else None
        if capture:
            ctx.ajouter(CaptureTableauSession(id=new_id(), session_id=session.id, panneau_id=panneau.id,
                                              lulufiles_file_id=capture, created_at=debut + timedelta(minutes=55)))
        ctx.ajouter(ResumeSessionLive(
            id=new_id(), session_id=session.id, created_at=debut + timedelta(hours=1),
            contenu=f"Séance de {classe.niveau} animée par {affectation.enseignant.prenom} {affectation.enseignant.nom} : "
                    f"{len(participants)} élève(s) connecté(s). Rappel de la définition du chapitre, un exemple détaillé au tableau "
                    "puis un exercice d'application ; une question sur la deuxième étape a été reprise en fin de séance.",
        ))
