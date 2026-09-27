"""Economie etudiante : Coffre-fort familial (UC-35), micro-jobs (UC-18/57), marketplace
(UC-20/21/22/58).

- micro-jobs : client adulte ou etudiant, PRESTATAIRE etudiant uniquement (jamais le client
  lui-meme) ; offre publiee EN_ATTENTE_PAIEMENT puis OUVERTE une fois payee (ou ANNULEE avant
  paiement), FERMEE quand un etudiant l'accepte ; mission : EN_COURS -> TERMINEE_DECLAREE
  (validation tacite a +5 j) -> VALIDEE -> PAYEE par l'A++ (reversement Mobile Money,
  seulement si le prestataire a renseigne son numero) ; ou CONTESTEE -> arbitrage A++ ;
- marketplace : vendeur et acheteur etudiants du MEME etablissement, 16 ans et plus ;
  reservation -> paiement -> remise declaree (+5 j) -> confirmee -> reversement par l'A+ ;
- Coffre-fort : quand un etudiant a un plafond, toute depense au-dessus du seuil a une
  validation parentale liee a la VRAIE depense (offre, transaction) : approuvee si la depense
  a abouti, en attente si elle attend le paiement, refusee si elle a ete annulee ; une
  alerte est levee si la depense de la semaine depasse le plafond hebdomadaire.
"""

from __future__ import annotations

from datetime import timedelta

from app.modules.coffre_fort.models import (
    AlerteDepassementPlafond,
    ModuleDepenseCoffreFort,
    PlafondFamilial,
    StatutValidationParentale,
    ValidationParentale,
)
from app.modules.etablissements.models import TypeEtablissement
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

from .contexte import Contexte, EleveInscrit, age_au, new_id
from .taxonomie import MOTIFS_CONTESTATION_MICRO_JOB, TITRES_OFFRES_MICRO_JOB

DELAI = timedelta(days=5)  # validation tacite (micro-jobs) / confirmation de reception (marketplace)

ARTICLES = {
    CategorieAnnonce.FOURNITURES_SCOLAIRES: (["Lot de cahiers 200 pages", "Calculatrice et kit de géométrie", "Sac à dos presque neuf"], (0.86, 0.93, 0.98)),
    CategorieAnnonce.MANUELS_LIVRES: (["Manuel d'algorithmique", "Code civil annoté", "Cours d'anatomie illustré", "Dictionnaire Le Robert"], (0.99, 0.93, 0.82)),
    CategorieAnnonce.VETEMENTS_UNIFORMES: (["Blouse de laboratoire", "Tenue de sport taille M", "Chaussures de sécurité (TP)"], (0.9, 0.97, 0.9)),
    CategorieAnnonce.ELECTRONIQUE: (["Ordinateur portable d'occasion", "Clé USB 64 Go", "Casque audio"], (0.92, 0.9, 0.98)),
    CategorieAnnonce.AUTRE: (["Vélo pour le campus", "Ventilateur de bureau", "Lampe de lecture"], (0.97, 0.95, 0.9)),
}


def _tx() -> str:
    return f"seed-{new_id()}"


def etudiants(ctx: Contexte) -> list[EleveInscrit]:
    return [i for etab_id, liste in ctx.inscrits_par_etab.items() for i in liste if i.etablissement.type == TypeEtablissement.UP]


def plafonds(ctx: Contexte, etab) -> None:
    """Appele juste apres les inscriptions d'une universite : les plafonds existent avant
    toute depense (actes, marketplace, micro-jobs), comme en production."""
    for inscrit in ctx.inscrits_par_etab[etab.id]:
        if ctx.rng.random() >= 0.25:
            continue
        seuil = ctx.rng.choice([None, 5000.0, 8000.0])
        hebdo = ctx.rng.choice([None, 10000.0, 20000.0]) if seuil else ctx.rng.choice([10000.0, 20000.0])
        plafond = PlafondFamilial(
            id=new_id(), tuteur_id=inscrit.eleve.tuteur_id, eleve_utilisateur_id=inscrit.utilisateur.id,
            plafond_hebdomadaire=hebdo, seuil_validation=seuil, created_at=ctx.debut_activite,
        )
        ctx.ajouter(plafond)
        ctx.plafonds[inscrit.utilisateur.id] = plafond


def validation(ctx: Contexte, inscrit: EleveInscrit, module, reference_id: str, montant: float, demande_le, issue: str) -> None:
    """issue : 'aboutie' | 'en_attente' | 'annulee'. Sans plafond ou sous le seuil : rien."""
    plafond = ctx.plafonds.get(inscrit.utilisateur.id)
    if plafond is None or plafond.seuil_validation is None or montant <= plafond.seuil_validation:
        return
    statut = {"aboutie": StatutValidationParentale.APPROUVEE, "en_attente": StatutValidationParentale.EN_ATTENTE,
              "annulee": StatutValidationParentale.REFUSEE}[issue]
    ctx.ajouter(ValidationParentale(
        id=new_id(), tuteur_id=inscrit.eleve.tuteur_id, eleve_utilisateur_id=inscrit.utilisateur.id, module=module,
        reference_id=reference_id, montant=montant, statut=statut,
        motif_refus="Dépense non prévue ce mois-ci, on en reparle à la maison." if statut == StatutValidationParentale.REFUSEE else None,
        decidee_at=demande_le + timedelta(hours=ctx.rng.randint(1, 20)) if statut != StatutValidationParentale.EN_ATTENTE else None,
        created_at=demande_le,
    ))


def micro_jobs(ctx: Contexte) -> None:
    pool_etudiants = etudiants(ctx)
    prestataires = [i for i in pool_etudiants if age_au(i.eleve.date_naissance, ctx.maintenant.date()) >= 18]
    if len(prestataires) < 2:
        return
    adultes = list(ctx.tuteurs.values()) + [u for liste in ctx.enseignants_par_etab.values() for u in liste]
    for _ in range(ctx.cfg.n_offres_micro_job):
        client_etudiant = ctx.rng.random() < 0.3
        inscrit_client = ctx.rng.choice(pool_etudiants) if client_etudiant else None
        client = inscrit_client.utilisateur if inscrit_client else ctx.rng.choice(adultes)
        publiee = ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=6))
        prix = float(ctx.rng.choice([2000, 3500, 5000, 7500, 10000]))
        offre = OffreMicroJob(
            id=new_id(), client_id=client.id, titre=ctx.rng.choice(TITRES_OFFRES_MICRO_JOB),
            description="Besoin ponctuel, horaires à convenir. Le paiement est séquestré jusqu'à validation du travail.",
            prix=prix, statut=StatutOffreMicroJob.EN_ATTENTE_PAIEMENT, paiement_confirme=False, created_at=publiee,
        )
        ctx.ajouter(offre)
        tirage = ctx.rng.random()
        if tirage < 0.1:
            issue = "en_attente"  # publiee, pas encore payee
        elif tirage < 0.17:
            offre.statut = StatutOffreMicroJob.ANNULEE
            issue = "annulee"
        else:
            offre.statut = StatutOffreMicroJob.OUVERTE
            offre.paiement_confirme = True
            offre.kkiapay_transaction_id = _tx()
            issue = "aboutie"
        if inscrit_client:
            validation(ctx, inscrit_client, ModuleDepenseCoffreFort.MICRO_JOB, offre.id, prix, publiee, issue)
            if issue == "aboutie":
                ctx.depense(inscrit_client.utilisateur.id, publiee, prix, ModuleDepenseCoffreFort.MICRO_JOB)
        if offre.statut != StatutOffreMicroJob.OUVERTE or ctx.rng.random() < 0.3:
            continue
        candidats = [p for p in prestataires if p.utilisateur.id != client.id]
        prestataire = ctx.rng.choice(candidats).utilisateur
        offre.statut = StatutOffreMicroJob.FERMEE
        acceptee = ctx.instant(publiee + timedelta(hours=2), ctx.maintenant - timedelta(hours=2))
        mission = MissionMicroJob(
            id=new_id(), offre_id=offre.id, prestataire_id=prestataire.id, statut=StatutMissionMicroJob.EN_COURS,
            prix_paye=prix, paiement_confirme=True, kkiapay_transaction_id=offre.kkiapay_transaction_id, created_at=acceptee,
        )
        ctx.ajouter(mission)
        if ctx.rng.random() < 0.2:
            continue  # toujours en cours
        declaree = ctx.instant(acceptee + timedelta(hours=6), ctx.maintenant - timedelta(hours=1))
        mission.date_declaration_fin = declaree
        mission.date_limite_validation = declaree + DELAI
        mission.statut = StatutMissionMicroJob.TERMINEE_DECLAREE
        if mission.date_limite_validation > ctx.maintenant and ctx.rng.random() < 0.4:
            continue  # le client a encore le temps de valider ou de contester
        if ctx.rng.random() < 0.15:
            # Contestation deposee avant l'echeance, puis arbitrage de l'A++ (ou en attente).
            contestation = ContestationMicroJob(
                id=new_id(), mission_id=mission.id, motif=ctx.rng.choice(MOTIFS_CONTESTATION_MICRO_JOB),
                statut=StatutContestationMicroJob.EN_ATTENTE, created_at=declaree + timedelta(days=1),
            )
            ctx.ajouter(contestation)
            mission.statut = StatutMissionMicroJob.CONTESTEE
            decision = ctx.rng.random()
            if decision < 0.35:
                contestation.statut = StatutContestationMicroJob.ACCEPTEE
                contestation.decision_motif = "Travail non conforme à l'offre : le client est remboursé."
                contestation.decision_par_id = ctx.admin_ministeriel.id
                mission.statut = StatutMissionMicroJob.REMBOURSEE
            elif decision < 0.6:
                contestation.statut = StatutContestationMicroJob.REJETEE
                contestation.decision_motif = "Travail conforme à l'offre : la mission est validée."
                contestation.decision_par_id = ctx.admin_ministeriel.id
                mission.statut = StatutMissionMicroJob.VALIDEE
        else:
            mission.statut = StatutMissionMicroJob.VALIDEE  # par le client, ou tacitement a l'echeance
        # Reversement Mobile Money par l'A++ : impossible sans numero renseigne.
        if mission.statut == StatutMissionMicroJob.VALIDEE and prestataire.telephone and ctx.rng.random() < 0.6:
            mission.statut = StatutMissionMicroJob.PAYEE
            mission.reference_paiement_prestataire = f"MOMO-{ctx.rng.randint(10**9, 10**10 - 1)}"


def marketplace(ctx: Contexte) -> None:
    for etab in ctx.etablissements:
        if etab.type != TypeEtablissement.UP:
            continue
        eligibles = [i for i in ctx.inscrits_par_etab[etab.id] if age_au(i.eleve.date_naissance, ctx.maintenant.date()) >= 16]
        if len(eligibles) < 2:
            continue
        admin = ctx.admin_par_etab[etab.id]
        for _ in range(ctx.cfg.annonces_par_universite):
            categorie = ctx.rng.choice(list(CategorieAnnonce))
            titres, teinte = ARTICLES[categorie]
            vendeur = ctx.rng.choice(eligibles)
            titre = ctx.rng.choice(titres)
            publiee = ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=4))
            annonce = AnnonceMarketplace(
                id=new_id(), etablissement_id=etab.id, vendeur_id=vendeur.utilisateur.id, titre=titre,
                description=f"{titre}, en vente entre étudiants de l'établissement. Remise en main propre sur le campus.",
                categorie=categorie, etat=ctx.rng.choice(list(EtatArticle)),
                prix=float(ctx.rng.choice([1000, 2500, 5000, 7500, 12000, 25000, 60000])),
                statut=StatutAnnonce.RETIREE if ctx.rng.random() < 0.05 else StatutAnnonce.DISPONIBLE, created_at=publiee,
            )
            ctx.ajouter(annonce)
            photo = ctx.fichiers.photo_article(categorie.value, titre.split(" ")[0], teinte)
            if photo:
                ctx.ajouter(PhotoAnnonceMarketplace(id=new_id(), annonce_id=annonce.id, lulufiles_file_id=photo, ordre=0))
            autres = [e for e in eligibles if e.utilisateur.id != vendeur.utilisateur.id]
            if ctx.rng.random() < 0.12:
                traite = ctx.rng.random() < 0.6
                ctx.ajouter(SignalementAnnonceMarketplace(
                    id=new_id(), annonce_id=annonce.id, signale_par_id=ctx.rng.choice(autres).utilisateur.id, traite=traite,
                    decision="Annonce vérifiée : conforme aux règles." if traite else None,
                    traite_par_id=admin.id if traite else None, created_at=publiee + timedelta(hours=5),
                ))
            if annonce.statut == StatutAnnonce.RETIREE or ctx.rng.random() >= 0.6:
                continue
            _transaction(ctx, annonce, ctx.rng.choice(autres), admin, publiee)


def _transaction(ctx: Contexte, annonce: AnnonceMarketplace, acheteur: EleveInscrit, admin, publiee) -> None:
    reservee = ctx.instant(publiee + timedelta(hours=1), ctx.maintenant - timedelta(hours=2))
    t = TransactionMarketplace(
        id=new_id(), annonce_id=annonce.id, acheteur_id=acheteur.utilisateur.id,
        statut=StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT, prix_paye=annonce.prix, paiement_confirme=False,
        created_at=reservee,
    )
    ctx.ajouter(t)
    annonce.statut = StatutAnnonce.RESERVEE
    tirage = ctx.rng.random()
    if tirage < 0.1:
        validation(ctx, acheteur, ModuleDepenseCoffreFort.MARKETPLACE, t.id, annonce.prix, reservee, "en_attente")
        return
    if tirage < 0.17:
        t.statut = StatutTransactionMarketplace.ANNULEE
        annonce.statut = StatutAnnonce.DISPONIBLE
        validation(ctx, acheteur, ModuleDepenseCoffreFort.MARKETPLACE, t.id, annonce.prix, reservee, "annulee")
        return
    validation(ctx, acheteur, ModuleDepenseCoffreFort.MARKETPLACE, t.id, annonce.prix, reservee, "aboutie")
    t.statut, t.paiement_confirme, t.kkiapay_transaction_id = StatutTransactionMarketplace.PAIEMENT_CONFIRME, True, _tx()
    ctx.depense(acheteur.utilisateur.id, reservee, annonce.prix, ModuleDepenseCoffreFort.MARKETPLACE)
    if ctx.rng.random() < 0.2:
        return
    remise = ctx.instant(reservee + timedelta(hours=3), ctx.maintenant - timedelta(hours=1))
    t.statut, t.date_remise_declaree, t.date_limite_confirmation = StatutTransactionMarketplace.REMISE_DECLAREE, remise, remise + DELAI
    if t.date_limite_confirmation > ctx.maintenant and ctx.rng.random() < 0.4:
        return  # en attente de confirmation de l'acheteur
    if ctx.rng.random() < 0.15:
        t.statut = StatutTransactionMarketplace.CONTESTEE
        contestation = ContestationMarketplace(
            id=new_id(), transaction_id=t.id, motif="L'article reçu ne correspond pas à la description de l'annonce.",
            statut=StatutContestationMarketplace.EN_ATTENTE, created_at=remise + timedelta(days=1),
        )
        ctx.ajouter(contestation)
        decision = ctx.rng.random()
        if decision < 0.35:
            contestation.statut, t.statut, annonce.statut = StatutContestationMarketplace.ACCEPTEE, StatutTransactionMarketplace.REMBOURSEE, StatutAnnonce.DISPONIBLE
            contestation.decision_motif, contestation.decision_par_id = "Contestation fondée : l'acheteur est remboursé.", admin.id
            return
        if decision < 0.6:
            contestation.statut, t.statut = StatutContestationMarketplace.REJETEE, StatutTransactionMarketplace.CONFIRMEE
            contestation.decision_motif, contestation.decision_par_id = "Article conforme à l'annonce : la vente est confirmée.", admin.id
        else:
            return  # contestation en attente d'arbitrage
    else:
        t.statut = StatutTransactionMarketplace.CONFIRMEE
    vendeur = ctx.utilisateurs[annonce.vendeur_id]
    if vendeur.telephone and ctx.rng.random() < 0.6:
        t.statut, t.reference_paiement_vendeur = StatutTransactionMarketplace.FINALISEE, f"MOMO-{ctx.rng.randint(10**9, 10**10 - 1)}"
        annonce.statut = StatutAnnonce.VENDUE


def alertes_plafond(ctx: Contexte) -> None:
    debut_semaine = ctx.maintenant - timedelta(days=ctx.maintenant.weekday(), hours=ctx.maintenant.hour, minutes=ctx.maintenant.minute)
    for eleve_id, plafond in ctx.plafonds.items():
        if plafond.plafond_hebdomadaire is None:
            continue
        depenses = sorted((d for d in ctx.depenses.get(eleve_id, []) if d[0] >= debut_semaine), key=lambda d: d[0])
        if sum(m for _, m, _ in depenses) > plafond.plafond_hebdomadaire:
            # Alerte levee par la depense qui fait franchir le plafond (coffre_fort/service.py).
            cumul = 0.0
            for quand, montant, module in depenses:
                cumul += montant
                if cumul > plafond.plafond_hebdomadaire:
                    ctx.ajouter(AlerteDepassementPlafond(
                        id=new_id(), tuteur_id=plafond.tuteur_id, eleve_utilisateur_id=eleve_id, module=module,
                        montant_semaine=cumul, plafond=plafond.plafond_hebdomadaire, created_at=quand,
                    ))
                    break
