"""Actes academiques (UC-10), transport et cantine (UC-11/12), billetterie (UC-17).

Regles reprises des routeurs :
- acte gratuit ou reclamation : EN_TRAITEMENT d'emblee ; acte payant : SOUMISE non payee,
  puis EN_TRAITEMENT une fois payee ; l'A+ ne tranche (ACCEPTEE/REJETEE) qu'une demande
  EN_TRAITEMENT ; un acte accepte porte son document final ;
- ticket : un seul par personne, par date et par service ; valide par le controleur
  uniquement le jour meme et s'il est paye ; rembourse/annule seulement avant la veille
  18 h ; reserve aux eleves de l'etablissement ;
- billet : un par personne et par evenement ; valide a l'entree seulement si paye ;
  l'annulation de l'evenement rembourse tous les billets ;
- controleurs : enseignants sous contrat de l'etablissement ou son A+.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.coffre_fort.models import ModuleDepenseCoffreFort
from app.modules.billetterie.models import BilletEvenement, Evenement, StatutBillet, StatutEvenement
from app.modules.controle_acces.models import DesignationControleur, ServiceControle
from app.modules.etablissements.models import Etablissement, TypeEtablissement
from app.modules.evaluations.models import Devoir
from app.modules.services_scolaires.models import LigneTransport, StatutTicket, TicketCantine, TicketTransport, TypeRepasCantine

from .contexte import Contexte, new_id
from .economie import validation
from .taxonomie import TITRES_EVENEMENTS

CATALOGUE_ACTES = [
    ("Attestation de scolarité", 0.0, "Aucune pièce requise."),
    ("Relevé de notes", 1000.0, "Copie de la carte d'élève ou d'étudiant."),
    ("Certificat de réussite", 1500.0, "Copie de la carte, photo d'identité."),
    ("Duplicata de diplôme", 7500.0, "Déclaration de perte, copie d'une pièce d'identité."),
]


def _tx() -> str:
    return f"seed-{new_id()}"


def actes(ctx: Contexte, etab: Etablissement, devoirs_par_classe: dict[str, list[Devoir]]) -> None:
    types = []
    for nom, prix, pieces in CATALOGUE_ACTES:
        if etab.type == TypeEtablissement.EP and nom == "Duplicata de diplôme":
            continue
        t = TypeActeAcademique(id=new_id(), etablissement_id=etab.id, nom=nom, prix=prix, pieces_requises=pieces,
                               created_at=ctx.debut_activite - timedelta(days=120))
        ctx.ajouter(t)
        types.append(t)
    for inscrit in ctx.inscrits_par_etab[etab.id]:
        if ctx.rng.random() >= 0.15:
            continue
        depot = ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=2))
        devoirs = [d for d in devoirs_par_classe.get(inscrit.classe.id, []) if d.date_limite < depot]
        reclamation = bool(devoirs) and ctx.rng.random() < 0.2
        type_acte = None if reclamation else ctx.rng.choice(types)
        gratuit = reclamation or type_acte.prix == 0
        if gratuit:
            statut = ctx.rng.choice([StatutDemandeActe.EN_TRAITEMENT, StatutDemandeActe.ACCEPTEE, StatutDemandeActe.REJETEE])
            paye = True
        else:
            statut = ctx.rng.choice([StatutDemandeActe.SOUMISE, StatutDemandeActe.EN_TRAITEMENT, StatutDemandeActe.ACCEPTEE, StatutDemandeActe.ACCEPTEE, StatutDemandeActe.REJETEE])
            paye = statut != StatutDemandeActe.SOUMISE
        devoir = ctx.rng.choice(devoirs) if reclamation else None
        demande = ctx.ajouter(DemandeActeAcademique(
            id=new_id(), eleve_id=inscrit.eleve.id, type_acte_id=type_acte.id if type_acte else None,
            est_reclamation=reclamation,
            reference_evaluation=devoir.titre if devoir else None,
            motif="La note ne tient pas compte de la deuxième partie de ma réponse." if reclamation else None,
            statut=statut, paiement_confirme=paye,
            kkiapay_transaction_id=_tx() if paye and not gratuit else None,
            motif_rejet=("Réclamation examinée : la note est maintenue après relecture." if reclamation
                         else "Dossier incomplet : pièce justificative manquante.") if statut == StatutDemandeActe.REJETEE else None,
            document_final_lulufiles_id=ctx.fichiers.acte(type_acte.nom) if statut == StatutDemandeActe.ACCEPTEE and type_acte else None,
            created_at=depot,
        ))
        if type_acte and type_acte.prix > 0 and etab.type == TypeEtablissement.UP:
            # Depense d'etudiant : validation parentale si elle depasse le seuil fixe par la famille.
            validation(ctx, inscrit, ModuleDepenseCoffreFort.ACTE, demande.id, type_acte.prix, depot,
                       "aboutie" if paye else "en_attente")
        if type_acte and paye and type_acte.prix > 0:
            ctx.depense(inscrit.utilisateur.id, depot, type_acte.prix, ModuleDepenseCoffreFort.ACTE)


def _controleur(ctx: Contexte, etab: Etablissement):
    enseignants = ctx.enseignants_par_etab[etab.id]
    return ctx.rng.choice(enseignants) if enseignants and ctx.rng.random() < 0.8 else ctx.admin_par_etab[etab.id]


def _limite_remboursement(jour) -> datetime:
    # Veille 18 h, heure du Benin (UTC+1) - services_scolaires/router.py
    return datetime.combine(jour - timedelta(days=1), datetime.min.time(), timezone.utc) + timedelta(hours=17)


def _ticket(ctx: Contexte, modele, champ_service: str, service_id: str, champ_date: str, prix: float, inscrit, jour, deja: set) -> None:
    cle = (inscrit.utilisateur.id, service_id, jour)
    if cle in deja:
        return
    deja.add(cle)
    aujourdhui = ctx.maintenant.date()
    achat = ctx.instant(max(ctx.debut_activite, _limite_remboursement(jour) - timedelta(days=12)),
                        min(ctx.maintenant, _limite_remboursement(jour)) - timedelta(minutes=30))
    if jour < aujourdhui:
        statut, paye = (StatutTicket.VALIDE, True) if ctx.rng.random() < 0.8 else (
            (StatutTicket.ACHETE, True) if ctx.rng.random() < 0.5 else (StatutTicket.REMBOURSE, ctx.rng.random() < 0.5)
        )
    elif jour == aujourdhui:
        statut, paye = (StatutTicket.VALIDE, True) if ctx.rng.random() < 0.4 else (StatutTicket.ACHETE, True)
    else:
        statut, paye = ctx.rng.choice([(StatutTicket.ACHETE, True), (StatutTicket.ACHETE, True), (StatutTicket.ACHETE, False), (StatutTicket.REMBOURSE, True)])
    ctx.ajouter(modele(**{
        "id": new_id(), champ_service: service_id, "utilisateur_id": inscrit.utilisateur.id, champ_date: jour,
        "statut": statut, "prix_paye": prix, "paiement_confirme": paye,
        "kkiapay_transaction_id": _tx() if paye else None, "created_at": achat,
    }))


def transport_et_cantine(ctx: Contexte, etab: Etablissement) -> None:
    inscrits = ctx.inscrits_par_etab[etab.id]
    if not inscrits:
        return
    universite = etab.type == TypeEtablissement.UP
    noms_lignes = ["Navette campus — Godomey", "Navette campus — Cotonou centre", "Navette campus — Calavi Kpota"] if universite         else ["Ligne A — Centre-ville", "Ligne B — Périphérie", "Ligne C — Quartiers résidentiels"]
    noms_repas = ["Restaurant universitaire — déjeuner", "Restaurant universitaire — dîner", "Petit-déjeuner"] if universite         else ["Déjeuner complet", "Petit-déjeuner", "Goûter"]
    services = []
    for nom in ctx.rng.sample(noms_lignes, k=2):
        ligne = LigneTransport(id=new_id(), etablissement_id=etab.id, nom=nom, prix=float(ctx.rng.choice([300, 500, 750])),
                               capacite_par_trajet=ctx.rng.randint(25, 45), created_at=ctx.rentree - timedelta(days=20))
        ctx.ajouter(ligne)
        services.append((TicketTransport, "ligne_id", ligne.id, "date_trajet", ligne.prix))
    for nom in ctx.rng.sample(noms_repas, k=2):
        repas = TypeRepasCantine(id=new_id(), etablissement_id=etab.id, nom=nom, prix=float(ctx.rng.choice([200, 350, 500])),
                                 capacite_par_jour=ctx.rng.randint(60, 150), created_at=ctx.rentree - timedelta(days=20))
        ctx.ajouter(repas)
        services.append((TicketCantine, "type_repas_id", repas.id, "date_service", repas.prix))
    deja: set = set()
    abonnes = ctx.rng.sample(inscrits, k=max(1, round(len(inscrits) * 0.3)))
    for inscrit in abonnes:
        modele, champ, service_id, champ_date, prix = ctx.rng.choice(services)
        for _ in range(ctx.rng.randint(2, 6)):
            jour = ctx.jour(-12, 6)
            if jour.weekday() >= 5:
                continue  # pas de service le week-end
            _ticket(ctx, modele, champ, service_id, champ_date, prix, inscrit, jour, deja)
    controleur = _controleur(ctx, etab)
    for service in (ServiceControle.TRANSPORT, ServiceControle.CANTINE):
        ctx.ajouter(DesignationControleur(id=new_id(), etablissement_id=etab.id, utilisateur_id=controleur.id, service=service,
                                          created_at=ctx.rentree - timedelta(days=5)))


def billetterie(ctx: Contexte, etab: Etablissement) -> None:
    communaute = [i.utilisateur for i in ctx.inscrits_par_etab[etab.id]]
    communaute += [ctx.tuteurs[i.eleve.tuteur_id] for i in ctx.inscrits_par_etab[etab.id]]
    communaute += ctx.enseignants_par_etab[etab.id] + [ctx.admin_par_etab[etab.id]]
    communaute = list({u.id: u for u in communaute}.values())
    for k in range(ctx.cfg.evenements_par_etab):
        passe = k == 0
        annule = not passe and ctx.rng.random() < 0.15
        date_heure = ctx.instant_scolaire(ctx.debut_activite + timedelta(days=3), ctx.maintenant - timedelta(days=1)) if passe \
            else ctx.instant_scolaire(ctx.maintenant + timedelta(days=4), ctx.maintenant + timedelta(days=45))
        prix = float(ctx.rng.choice([0, 500, 1000, 2000]))
        enseignants = ctx.enseignants_par_etab[etab.id]
        evenement = Evenement(
            id=new_id(), etablissement_id=etab.id, titre=ctx.rng.choice(TITRES_EVENEMENTS),
            description="Événement ouvert aux élèves, aux familles et au personnel de l'établissement.",
            lieu=ctx.rng.choice(["Cour principale", "Salle polyvalente", "Terrain de sport"]),
            date_heure=date_heure, capacite_max=ctx.rng.randint(80, 300), prix_billet=prix,
            statut=StatutEvenement.ANNULE if annule else StatutEvenement.OUVERT,
            parrain_utilisateur_id=ctx.rng.choice(enseignants).id if enseignants and ctx.rng.random() < 0.4 else None,
            created_at=min(date_heure, ctx.maintenant) - timedelta(days=ctx.rng.randint(10, 25)),
        )
        ctx.ajouter(evenement)
        acheteurs = ctx.rng.sample(communaute, k=min(len(communaute), ctx.rng.randint(5, 25), evenement.capacite_max))
        for u in acheteurs:
            achat = ctx.instant(evenement.created_at, min(date_heure, ctx.maintenant) - timedelta(hours=1))
            if annule:
                statut, paye = StatutBillet.REMBOURSE, prix > 0 and ctx.rng.random() < 0.8
            elif passe:
                statut, paye = (StatutBillet.VALIDE, True) if ctx.rng.random() < 0.85 else (StatutBillet.ACHETE, True)
            else:
                paye = prix == 0 or ctx.rng.random() < 0.8
                statut = StatutBillet.ACHETE
            paye = paye or prix == 0
            ctx.ajouter(BilletEvenement(
                id=new_id(), evenement_id=evenement.id, utilisateur_id=u.id, statut=statut, prix_paye=prix,
                paiement_confirme=paye, kkiapay_transaction_id=_tx() if paye and prix > 0 else None, created_at=achat,
            ))
        if not annule:
            ctx.ajouter(DesignationControleur(
                id=new_id(), etablissement_id=etab.id, utilisateur_id=_controleur(ctx, etab).id,
                service=ServiceControle.EVENEMENT, evenement_id=evenement.id, created_at=evenement.created_at,
            ))
