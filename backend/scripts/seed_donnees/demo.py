"""Scenarios GARANTIS pour les comptes de demonstration (quels que soient --scale et le
tirage aleatoire) : chaque ecran de ces comptes a quelque chose a montrer, et chaque file
d'attente d'administration contient au moins un element a traiter.

Tout est construit avec les memes regles que le reste du seed (verifier_seed.py le
controle de la meme facon)."""

from __future__ import annotations

from datetime import timedelta

from app.modules.coffre_fort.models import ModuleDepenseCoffreFort
from app.modules.billetterie.models import BilletEvenement, Evenement, StatutBillet, StatutEvenement
from app.modules.cours_direct.models import SessionLive, StatutSessionLive
from app.modules.marketplace.models import (
    AnnonceMarketplace,
    CategorieAnnonce,
    ContestationMarketplace,
    EtatArticle,
    PhotoAnnonceMarketplace,
    SignalementAnnonceMarketplace,
    StatutAnnonce,
    StatutContestationMarketplace,
    StatutTransactionMarketplace,
    TransactionMarketplace,
)
from app.modules.micro_jobs.models import (
    ContestationMicroJob,
    MissionMicroJob,
    OffreMicroJob,
    StatutContestationMicroJob,
    StatutMissionMicroJob,
    StatutOffreMicroJob,
)
from app.modules.pedagogie.models import (
    MessageElProfessor,
    MessageElProfessorFamille,
    MessageElProfessorTuteur,
    RoleMessageElProfessor,
    RoleMessageElProfessorFamille,
    RoleMessageElProfessorTuteur,
    SessionElProfessor,
    SessionElProfessorFamille,
    SessionElProfessorTuteur,
)
from app.modules.recrutement.models import Candidature, Contestation, Poste, StatutCandidature, StatutContestation, StatutPoste
from app.modules.services_scolaires.models import LigneTransport, StatutTicket, TicketTransport

from .contexte import Contexte, EleveInscrit, age_au, new_id
from .economie import ARTICLES, DELAI

REF = "demo"


def _tx() -> str:
    return f"seed-{new_id()}"


def _el_professor_eleve(ctx: Contexte, inscrit: EleveInscrit) -> None:
    debut = ctx.maintenant - timedelta(days=2, hours=3)
    session = ctx.ajouter(SessionElProfessor(
        id=new_id(), eleve_utilisateur_id=inscrit.utilisateur.id, cours_id=None, sujet="Préparer mes examens", created_at=debut,
    ))
    tours = [
        (RoleMessageElProfessor.ELEVE, "Comment préparer efficacement mes examens de fin de semestre ?"),
        (RoleMessageElProfessor.ASSISTANT, "Voici une méthode en trois temps :\n\n1. **Planifie** : liste tes matières et leurs coefficients, puis répartis tes révisions sur trois semaines.\n2. **Révise activement** : fiches de synthèse, exercices corrigés, sujets des années précédentes.\n3. **Teste-toi** : un examen blanc chronométré la dernière semaine.\n\nVeux-tu qu'on construise ton planning ensemble ?"),
    ]
    for k, (role, contenu) in enumerate(tours):
        ctx.ajouter(MessageElProfessor(id=new_id(), session_id=session.id, role=role, contenu=contenu, created_at=debut + timedelta(minutes=k)))


def _tuteur_et_famille(ctx: Contexte, inscrit: EleveInscrit) -> None:
    tuteur_id = inscrit.eleve.tuteur_id
    debut = ctx.maintenant - timedelta(days=3)
    s = ctx.ajouter(SessionElProfessorTuteur(id=new_id(), tuteur_id=tuteur_id, eleve_utilisateur_id=inscrit.utilisateur.id,
                                             sujet="Accompagner sa scolarité", created_at=debut))
    ctx.ajouter(MessageElProfessorTuteur(id=new_id(), session_id=s.id, role=RoleMessageElProfessorTuteur.TUTEUR, created_at=debut,
                                         contenu=f"Comment encourager {inscrit.eleve.prenom} sans lui mettre trop de pression ?"))
    ctx.ajouter(MessageElProfessorTuteur(id=new_id(), session_id=s.id, role=RoleMessageElProfessorTuteur.ASSISTANT, created_at=debut + timedelta(minutes=1),
                                         contenu="Valorisez les efforts plutôt que les seules notes, fixez ensemble des objectifs courts et réalistes, et gardez un moment d'échange régulier sur ce qui se passe en classe."))
    rejointe = ctx.maintenant - timedelta(days=1, hours=20)
    f = ctx.ajouter(SessionElProfessorFamille(id=new_id(), tuteur_id=tuteur_id, eleve_utilisateur_id=inscrit.utilisateur.id,
                                              sujet="Organisation de la semaine", created_at=rejointe - timedelta(hours=4), rejointe_le=rejointe))
    for k, (role, contenu) in enumerate([
        (RoleMessageElProfessorFamille.TUTEUR, "Organisons ensemble le temps de travail à la maison."),
        (RoleMessageElProfessorFamille.ELEVE, "D'accord, mais je veux garder le mercredi après-midi pour le sport."),
        (RoleMessageElProfessorFamille.ASSISTANT, f"Bonne base de discussion ! {inscrit.eleve.prenom}, propose deux créneaux de travail par jour ; côté parent, validez ce planning et faites un point rapide le dimanche soir."),
    ]):
        ctx.ajouter(MessageElProfessorFamille(id=new_id(), session_id=f.id, role=role, contenu=contenu, created_at=rejointe + timedelta(minutes=k * 3)))


def _ticket_du_jour(ctx: Contexte, inscrit: EleveInscrit) -> None:
    """Un ticket paye pour aujourd'hui (le controleur peut le valider) et un pour demain."""
    ligne = next((x for x in ctx.objets(LigneTransport) if x.etablissement_id == inscrit.etablissement.id), None)
    if ligne is None:
        return
    deja = {(t.date_trajet) for t in ctx.objets(TicketTransport) if t.utilisateur_id == inscrit.utilisateur.id and t.ligne_id == ligne.id
            and t.statut in (StatutTicket.ACHETE, StatutTicket.VALIDE)}
    for decalage in (0, 1):
        jour = (ctx.maintenant + timedelta(days=decalage)).date()
        if jour in deja:
            continue
        ctx.ajouter(TicketTransport(
            id=new_id(), ligne_id=ligne.id, utilisateur_id=inscrit.utilisateur.id, date_trajet=jour, statut=StatutTicket.ACHETE,
            prix_paye=ligne.prix, paiement_confirme=True, kkiapay_transaction_id=_tx(), created_at=ctx.maintenant - timedelta(days=2),
        ))


def _billet(ctx: Contexte, inscrit: EleveInscrit) -> None:
    evenement = next((e for e in ctx.objets(Evenement) if e.etablissement_id == inscrit.etablissement.id
                      and e.statut == StatutEvenement.OUVERT and e.date_heure > ctx.maintenant), None)
    if evenement is None or any(b.evenement_id == evenement.id and b.utilisateur_id == inscrit.utilisateur.id for b in ctx.objets(BilletEvenement)):
        return
    ctx.ajouter(BilletEvenement(
        id=new_id(), evenement_id=evenement.id, utilisateur_id=inscrit.utilisateur.id, statut=StatutBillet.ACHETE,
        prix_paye=evenement.prix_billet, paiement_confirme=True,
        kkiapay_transaction_id=_tx() if evenement.prix_billet > 0 else None, created_at=ctx.maintenant - timedelta(days=1),
    ))


def _annonce(ctx: Contexte, vendeur: EleveInscrit, categorie: CategorieAnnonce, titre: str, prix: float, publiee) -> AnnonceMarketplace:
    annonce = ctx.ajouter(AnnonceMarketplace(
        id=new_id(), etablissement_id=vendeur.etablissement.id, vendeur_id=vendeur.utilisateur.id, titre=titre,
        description=f"{titre}, en vente entre étudiants. Remise en main propre sur le campus.", categorie=categorie,
        etat=EtatArticle.TRES_BON_ETAT, prix=prix, statut=StatutAnnonce.DISPONIBLE, created_at=publiee,
    ))
    photo = ctx.fichiers.photo_article(categorie.value, titre.split(" ")[0], ARTICLES[categorie][1])
    if photo:
        ctx.ajouter(PhotoAnnonceMarketplace(id=new_id(), annonce_id=annonce.id, lulufiles_file_id=photo, ordre=0))
    return annonce


def _vente(ctx: Contexte, annonce: AnnonceMarketplace, acheteur: EleveInscrit, statut: StatutTransactionMarketplace) -> TransactionMarketplace:
    reservee = annonce.created_at + timedelta(hours=5)
    remise = ctx.maintenant - timedelta(days=1) if statut == StatutTransactionMarketplace.REMISE_DECLAREE else reservee + timedelta(days=1)
    t = ctx.ajouter(TransactionMarketplace(
        id=new_id(), annonce_id=annonce.id, acheteur_id=acheteur.utilisateur.id, statut=statut, prix_paye=annonce.prix,
        paiement_confirme=True, kkiapay_transaction_id=_tx(), date_remise_declaree=remise, date_limite_confirmation=remise + DELAI,
        created_at=reservee,
    ))
    annonce.statut = StatutAnnonce.RESERVEE
    return t


def marketplace_uac(ctx: Contexte, demo: EleveInscrit) -> None:
    """Pour l'etudiant de demo : une annonce en vente, un achat a confirmer, une vente a
    reverser (file de l'A+) ; pour l'A+ UAC : une contestation et un signalement a traiter."""
    camarades = [i for i in ctx.inscrits_par_etab[demo.etablissement.id]
                 if i.utilisateur.id != demo.utilisateur.id and i.utilisateur.telephone
                 and age_au(i.eleve.date_naissance, ctx.maintenant.date()) >= 16]
    if len(camarades) < 2:
        return
    a, b = camarades[0], camarades[1]
    debut = ctx.maintenant - timedelta(days=9)
    _annonce(ctx, demo, CategorieAnnonce.MANUELS_LIVRES, "Manuel d'algorithmique (2e édition)", 7500.0, debut)
    achat = _annonce(ctx, a, CategorieAnnonce.ELECTRONIQUE, "Clé USB 64 Go", 4000.0, debut)
    _vente(ctx, achat, demo, StatutTransactionMarketplace.REMISE_DECLAREE)  # l'etudiant de demo peut confirmer
    ctx.depense(demo.utilisateur.id, achat.created_at + timedelta(hours=5), achat.prix, ModuleDepenseCoffreFort.MARKETPLACE)
    vendue = _annonce(ctx, demo, CategorieAnnonce.FOURNITURES_SCOLAIRES, "Calculatrice scientifique", 9000.0, debut)
    _vente(ctx, vendue, b, StatutTransactionMarketplace.CONFIRMEE)  # a reverser par l'A+
    litige = _annonce(ctx, b, CategorieAnnonce.VETEMENTS_UNIFORMES, "Blouse de laboratoire", 3500.0, debut)
    t = _vente(ctx, litige, a, StatutTransactionMarketplace.CONTESTEE)
    ctx.ajouter(ContestationMarketplace(id=new_id(), transaction_id=t.id, statut=StatutContestationMarketplace.EN_ATTENTE,
                                        motif="La blouse reçue est tachée, contrairement à la description.",
                                        created_at=t.date_remise_declaree + timedelta(hours=10)))
    signalee = _annonce(ctx, a, CategorieAnnonce.AUTRE, "Vélo pour le campus", 45000.0, debut)
    ctx.ajouter(SignalementAnnonceMarketplace(id=new_id(), annonce_id=signalee.id, signale_par_id=b.utilisateur.id, traite=False,
                                              created_at=debut + timedelta(days=1)))


def micro_jobs_uac(ctx: Contexte, demo: EleveInscrit) -> None:
    """Une offre ouverte a accepter, une mission validee a payer (file de l'A++), une
    mission declaree terminee, un litige a arbitrer."""
    clients = [t for t in ctx.tuteurs.values() if t.id != demo.eleve.tuteur_id][:3]
    if len(clients) < 3 or age_au(demo.eleve.date_naissance, ctx.maintenant.date()) < 18:
        return
    publiee = ctx.maintenant - timedelta(days=8)
    ctx.ajouter(OffreMicroJob(id=new_id(), client_id=clients[0].id, titre="Cours particulier d'algorithmique (L1)",
                              description="Deux séances de 2 h cette semaine, au campus ou en ligne.", prix=6000.0,
                              statut=StatutOffreMicroJob.OUVERTE, paiement_confirme=True, kkiapay_transaction_id=_tx(), created_at=publiee))
    for client, statut, titre in (
        (clients[1], StatutMissionMicroJob.VALIDEE, "Saisie et mise en page d'un mémoire"),
        (clients[2], StatutMissionMicroJob.TERMINEE_DECLAREE, "Initiation à l'informatique pour un collégien"),
        (clients[0], StatutMissionMicroJob.CONTESTEE, "Traduction d'un dossier de candidature"),
    ):
        tx = _tx()
        offre = ctx.ajouter(OffreMicroJob(id=new_id(), client_id=client.id, titre=titre, description="Mission ponctuelle, paiement séquestré.",
                                          prix=8000.0, statut=StatutOffreMicroJob.FERMEE, paiement_confirme=True, kkiapay_transaction_id=tx,
                                          created_at=publiee))
        declaree = ctx.maintenant - timedelta(days=2) if statut != StatutMissionMicroJob.VALIDEE else publiee + timedelta(days=3)
        mission = ctx.ajouter(MissionMicroJob(
            id=new_id(), offre_id=offre.id, prestataire_id=demo.utilisateur.id, statut=statut, prix_paye=8000.0, paiement_confirme=True,
            kkiapay_transaction_id=tx, date_declaration_fin=declaree, date_limite_validation=declaree + DELAI,
            created_at=publiee + timedelta(hours=6),
        ))
        if statut == StatutMissionMicroJob.CONTESTEE:
            ctx.ajouter(ContestationMicroJob(id=new_id(), mission_id=mission.id, statut=StatutContestationMicroJob.EN_ATTENTE,
                                             motif="La traduction comporte plusieurs contresens.", created_at=declaree + timedelta(hours=12)))


def contestation_recrutement(ctx: Contexte, etab) -> None:
    """Une contestation de candidature en attente de decision pour l'A+ de l'etablissement."""
    postes_ouverts = {p.id for p in ctx.objets(Poste) if p.etablissement_id == etab.id and p.statut == StatutPoste.OUVERT}
    candidatures = {c.id: c for c in ctx.objets(Candidature)}
    if any(c.statut == StatutContestation.EN_ATTENTE and candidatures[c.candidature_id].poste_id in postes_ouverts
           for c in ctx.objets(Contestation)):
        return
    deja_contestees = {c.candidature_id for c in ctx.objets(Contestation)}
    rejetee = next((c for c in ctx.objets(Candidature) if c.statut == StatutCandidature.REJETEE and c.poste_id in postes_ouverts
                    and c.id not in deja_contestees
                    and c.rejetee_le and c.rejetee_le > ctx.maintenant - timedelta(days=5)), None)
    if rejetee is None:
        return
    ctx.ajouter(Contestation(id=new_id(), candidature_id=rejetee.id, statut=StatutContestation.EN_ATTENTE, created_at=rejetee.rejetee_le + timedelta(hours=2),
                             motif="Mon diplôme a été mal lu : la mention figure bien sur la copie transmise."))
    rejetee.statut = StatutCandidature.EN_EVALUATION


def session_live_a_venir(ctx: Contexte, enseignant, classe_id: str) -> None:
    if any(s.enseignant_id == enseignant.id and s.statut == StatutSessionLive.PLANIFIEE for s in ctx.objets(SessionLive)):
        return
    debut = ctx.maintenant + timedelta(days=2, hours=2)
    ctx.ajouter(SessionLive(id=new_id(), classe_id=classe_id, enseignant_id=enseignant.id, date_heure=debut,
                            statut=StatutSessionLive.PLANIFIEE, created_at=ctx.maintenant - timedelta(days=1)))


def garantir(ctx: Contexte) -> None:
    uac = ctx.uac
    etudiant = ctx.eleves_demo.get("uac")
    if etudiant:
        _el_professor_eleve(ctx, etudiant)
        _tuteur_et_famille(ctx, etudiant)
        _ticket_du_jour(ctx, etudiant)
        _billet(ctx, etudiant)
        marketplace_uac(ctx, etudiant)
        micro_jobs_uac(ctx, etudiant)
    contestation_recrutement(ctx, uac)
    for cle in ("lycee", "primaire"):
        inscrit = ctx.eleves_demo.get(cle)
        if inscrit:
            _el_professor_eleve(ctx, inscrit)
            _tuteur_et_famille(ctx, inscrit)
            _ticket_du_jour(ctx, inscrit)
            _billet(ctx, inscrit)
    for enseignant, classe_id in ctx.enseignants_demo:
        session_live_a_venir(ctx, enseignant, classe_id)
