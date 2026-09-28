"""Boite « A traiter » : tout ce qui attend un administrateur, dans une seule vue.

Au lieu de parcourir une dizaine d'ecrans (inscriptions, recrutement, actes, moderation,
litiges, reversements...), l'A+ (pour son etablissement) et l'A++ (au niveau national)
recoivent la liste de leurs files d'attente, chacune avec ses elements, ce que l'IA a deja
prepare (triage, avis, analyse) et les actions groupees disponibles. Chaque section
n'apparait que si elle contient quelque chose.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.moderation import ORDRE_GRAVITE
from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.billetterie.models import BilletEvenement, Evenement, StatutBillet
from app.modules.etablissements.models import AdminEtablissement, AffectationEnseignant, Classe, annee_academique_courante
from app.modules.evaluations.models import ReferentielCoefficient, StatutReferentiel
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.marketplace.models import (
    AnnonceMarketplace,
    ContestationMarketplace,
    SignalementAnnonceMarketplace,
    StatutContestationMarketplace,
    StatutTransactionMarketplace,
    TransactionMarketplace,
)
from app.modules.messagerie.models import Conversation, Message, SignalementMessage, TypeConversation
from app.modules.micro_jobs.models import (
    ContestationMicroJob,
    MissionMicroJob,
    OffreMicroJob,
    StatutContestationMicroJob,
    StatutMissionMicroJob,
)
from app.modules.pedagogie.models import AlerteElProfessor
from app.modules.recrutement.automatisation import TENTATIVES_MAX
from app.modules.recrutement.models import (
    Candidature,
    Contestation,
    Contrat,
    DocumentCandidature,
    Poste,
    PropositionReconduction,
    StatutCandidature,
    StatutContestation,
    StatutContrat,
    StatutDocument,
    StatutPoste,
    StatutVerificationCasier,
    VerificationCasierJudiciaire,
)
from app.modules.services_scolaires.models import LigneTransport, StatutTicket, TicketCantine, TicketTransport, TypeRepasCantine

router = APIRouter(tags=["administration"])

MAX_ELEMENTS = 50


class Element(BaseModel):
    id: str
    libelle: str
    detail: str | None = None
    ia: str | None = None  # ce que l'IA a prepare (triage, avis, analyse)
    ia_niveau: str | None = None  # "elevee" | "moyenne" | "faible" | "acceptee" | "rejetee"
    groupe: str | None = None  # regroupement (beneficiaire d'un reversement...)
    montant: float | None = None


class Section(BaseModel):
    cle: str
    titre: str
    description: str
    urgent: bool = False
    nombre: int
    elements: list[Element]


def _nom(u: Utilisateur | None) -> str:
    return f"{u.prenom} {u.nom}" if u else "—"


def _section(cle: str, titre: str, description: str, elements: list[Element], urgent: bool = False) -> Section | None:
    if not elements:
        return None
    return Section(cle=cle, titre=titre, description=description, urgent=urgent, nombre=len(elements), elements=elements[:MAX_ELEMENTS])


def _sections_etablissement(db: Session, etab_id: str) -> list[Section | None]:
    annee = annee_academique_courante()
    classes = {c.id: c for c in db.query(Classe).filter(Classe.etablissement_id == etab_id)}
    libelle_classe = {k: c.niveau + (f" — {c.filiere}" if c.filiere else "") for k, c in classes.items()}
    sections: list[Section | None] = []

    # Inscriptions
    inscriptions = (
        db.query(Inscription, Eleve)
        .join(Eleve, Eleve.id == Inscription.eleve_id)
        .filter(Inscription.classe_id.in_(list(classes)), Inscription.statut == StatutInscription.SOUMISE)
        .order_by(Inscription.created_at)
        .all()
    )
    sections.append(_section(
        "inscriptions", "Inscriptions à valider",
        "Validez-les en lot (par ordre d'arrivée, dans la limite des places), ou activez l'admission automatique.",
        [Element(id=i.id, libelle=f"{e.prenom} {e.nom}", detail=f"{libelle_classe[i.classe_id]} — déposée le {i.created_at:%d/%m/%Y}", groupe=i.classe_id)
         for i, e in inscriptions],
    ))

    # Recrutement
    postes = {p.id: p for p in db.query(Poste).filter(Poste.etablissement_id == etab_id)}
    candidatures = {c.id: c for c in db.query(Candidature).filter(Candidature.poste_id.in_(list(postes)))} if postes else {}
    enseignants = {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_({c.enseignant_id for c in candidatures.values()}))} if candidatures else {}
    casiers = {v.candidature_id: v for v in db.query(VerificationCasierJudiciaire).filter(VerificationCasierJudiciaire.candidature_id.in_(list(candidatures)))} if candidatures else {}
    sections.append(_section(
        "casiers", "Casiers judiciaires à examiner",
        "Seule étape du recrutement qui reste entièrement humaine (données pénales, jamais transmises à l'IA).",
        [Element(id=c.id, libelle=_nom(enseignants.get(c.enseignant_id)), detail=postes[c.poste_id].titre)
         for c in candidatures.values() if c.statut != StatutCandidature.REJETEE and (v := casiers.get(c.id))
         and v.statut == StatutVerificationCasier.EN_ATTENTE and v.contenu_chiffre is not None],
        urgent=True,
    ))
    sections.append(_section(
        "a_recruter", "Candidats prêts à recruter",
        "Casier conforme et dossier noté : « Recruter » crée le contrat pré-rempli (syllabus rédigé par l'IA).",
        sorted([Element(id=c.id, libelle=_nom(enseignants.get(c.enseignant_id)), detail=f"{postes[c.poste_id].titre} — score {c.score:.0f}/100",
                        groupe=c.poste_id)
                for c in candidatures.values() if c.statut == StatutCandidature.EN_EVALUATION and c.score is not None
                and postes[c.poste_id].statut == StatutPoste.OUVERT and (v := casiers.get(c.id)) and v.statut == StatutVerificationCasier.CONFORME],
               key=lambda e: e.detail or ""),
    ))
    documents = db.query(DocumentCandidature).filter(
        DocumentCandidature.candidature_id.in_(list(candidatures)), DocumentCandidature.statut == StatutDocument.ECHEC_NOTATION,
    ).all() if candidatures else []
    sections.append(_section(
        "notation_manuelle", "Documents à noter à la main",
        f"L'IA a échoué {TENTATIVES_MAX} fois (nouvel essai automatique chaque heure avant cela).",
        [Element(id=d.id, libelle=_nom(enseignants.get(candidatures[d.candidature_id].enseignant_id)), detail=d.type_document)
         for d in documents if d.tentatives_notation >= TENTATIVES_MAX or d.lulufiles_file_id is None],
    ))
    contestations = db.query(Contestation).filter(
        Contestation.candidature_id.in_(list(candidatures)), Contestation.statut == StatutContestation.EN_ATTENTE,
    ).all() if candidatures else []
    sections.append(_section(
        "contestations_recrutement", "Contestations de candidature", "À trancher : acceptée (dossier réexaminé) ou rejetée (motif requis).",
        [Element(id=c.id, libelle=_nom(enseignants.get(candidatures[c.candidature_id].enseignant_id)), detail=c.motif) for c in contestations],
    ))
    fenetre = date.today() + timedelta(days=30)
    deja = {p.contrat_precedent_id for p in db.query(PropositionReconduction)}
    a_reconduire = db.query(Contrat).filter(
        Contrat.etablissement_id == etab_id, Contrat.statut == StatutContrat.SIGNE, Contrat.date_fin <= fenetre, Contrat.date_fin >= date.today(),
    ).all()
    sections.append(_section(
        "reconductions", "Contrats arrivant à échéance", "« Tout reconduire » propose un nouveau contrat à chaque enseignant, qui re-signe.",
        [Element(id=k.id, libelle=_nom(db.get(Utilisateur, k.enseignant_id)), detail=f"fin le {k.date_fin:%d/%m/%Y}")
         for k in a_reconduire if k.id not in deja],
    ))

    # Affectations
    classes_courantes = [k for k, c in classes.items() if c.annee_academique == annee]
    avec_principal = {a.classe_id for a in db.query(AffectationEnseignant).filter(
        AffectationEnseignant.classe_id.in_(classes_courantes), AffectationEnseignant.est_professeur_principal.is_(True))}
    sections.append(_section(
        "affectations", "Classes sans professeur principal", "Une proposition d'affectations est calculée : appliquez-la en un clic.",
        [Element(id=k, libelle=libelle_classe[k]) for k in classes_courantes if k not in avec_principal],
    ))

    # Actes
    eleve_ids = [i.eleve_id for i in db.query(Inscription.eleve_id).filter(Inscription.classe_id.in_(list(classes))).distinct()]
    demandes = db.query(DemandeActeAcademique).filter(
        DemandeActeAcademique.eleve_id.in_(eleve_ids), DemandeActeAcademique.statut == StatutDemandeActe.EN_TRAITEMENT,
    ).all() if eleve_ids else []
    types = {t.id: t for t in db.query(TypeActeAcademique).filter(TypeActeAcademique.etablissement_id == etab_id)}
    sections.append(_section(
        "actes", "Actes et réclamations à traiter",
        "Les attestations et relevés de notes sont livrés automatiquement ; restent ici les autres actes et les réclamations (avis de l'IA joint).",
        [Element(id=d.id, libelle=f"{d.eleve.prenom} {d.eleve.nom}",
                 detail=("Réclamation : " + (d.reference_evaluation or "")) if d.est_reclamation else types[d.type_acte_id].nom if d.type_acte_id in types else "Acte",
                 ia=d.analyse_ia,
                 # "auto" : acte a modele dont la livraison automatique a echoue, relancable en un clic.
                 groupe="auto" if d.type_acte_id in types and types[d.type_acte_id].modele_document else None)
         for d in demandes],
    ))

    # Moderation
    signalements = []
    for s, m, conv in (
        db.query(SignalementMessage, Message, Conversation)
        .join(Message, Message.id == SignalementMessage.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(SignalementMessage.traite.is_(False))
        .all()
    ):
        if conv.type == TypeConversation.GROUPE_CLASSE and conv.classe_id not in classes:
            continue
        if conv.type == TypeConversation.DM:
            from app.modules.messagerie.router import _etablissements_concernes

            if etab_id not in _etablissements_concernes(db, conv):
                continue
        signalements.append(Element(id=s.id, libelle=m.contenu[:120], ia=s.ia_resume, ia_niveau=s.ia_gravite, detail=s.ia_decision))
    sections.append(_section(
        "signalements_messages", "Messages signalés", "Triés par gravité par l'IA ; « Appliquer les suggestions » traite en lot tout ce qui n'est pas à examiner.",
        sorted(signalements, key=lambda e: ORDRE_GRAVITE.get(e.ia_niveau, 3)),
        urgent=any(e.ia_niveau == "elevee" for e in signalements),
    ))
    annonces = {a.id: a for a in db.query(AnnonceMarketplace).filter(AnnonceMarketplace.etablissement_id == etab_id)}
    sig_annonces = db.query(SignalementAnnonceMarketplace).filter(
        SignalementAnnonceMarketplace.annonce_id.in_(list(annonces)), SignalementAnnonceMarketplace.traite.is_(False)
    ).all() if annonces else []
    sections.append(_section(
        "signalements_annonces", "Annonces signalées", "Même principe : suggestion de l'IA, application en lot.",
        sorted([Element(id=s.id, libelle=annonces[s.annonce_id].titre, ia=s.ia_resume, ia_niveau=s.ia_gravite, detail=s.ia_decision) for s in sig_annonces],
               key=lambda e: ORDRE_GRAVITE.get(e.ia_niveau, 3)),
    ))

    # Marketplace : litiges et reversements
    transactions = {t.id: t for t in db.query(TransactionMarketplace).filter(TransactionMarketplace.annonce_id.in_(list(annonces)))} if annonces else {}
    litiges = db.query(ContestationMarketplace).filter(
        ContestationMarketplace.transaction_id.in_(list(transactions)), ContestationMarketplace.statut == StatutContestationMarketplace.EN_ATTENTE,
    ).all() if transactions else []
    sections.append(_section(
        "litiges_marketplace", "Litiges de la marketplace", "Avis de l'IA joint ; un remboursement accordé est versé automatiquement par Kkiapay.",
        [Element(id=c.id, libelle=annonces[transactions[c.transaction_id].annonce_id].titre, detail=c.motif,
                 ia=c.ia_justification, ia_niveau=c.ia_decision, montant=transactions[c.transaction_id].prix_paye) for c in litiges],
    ))
    vendeurs = {}
    a_reverser = [t for t in transactions.values() if t.statut == StatutTransactionMarketplace.CONFIRMEE]
    for t in a_reverser:
        vendeurs.setdefault(annonces[t.annonce_id].vendeur_id, db.get(Utilisateur, annonces[t.annonce_id].vendeur_id))
    sections.append(_section(
        "reversements_marketplace", "Ventes à reverser aux vendeurs",
        "Regroupées par vendeur : un seul virement Mobile Money et une seule référence pour toutes ses ventes.",
        [Element(id=t.id, libelle=annonces[t.annonce_id].titre, montant=t.prix_paye, groupe=annonces[t.annonce_id].vendeur_id,
                 detail=f"{_nom(vendeurs[annonces[t.annonce_id].vendeur_id])} — {vendeurs[annonces[t.annonce_id].vendeur_id].telephone or 'numéro Mobile Money non renseigné'}")
         for t in a_reverser],
    ))

    # Remboursements que Kkiapay n'a pas pu faire automatiquement
    manuels: list[Element] = []
    lignes = {x.id for x in db.query(LigneTransport).filter(LigneTransport.etablissement_id == etab_id)}
    repas = {x.id for x in db.query(TypeRepasCantine).filter(TypeRepasCantine.etablissement_id == etab_id)}
    evenements = {x.id: x for x in db.query(Evenement).filter(Evenement.etablissement_id == etab_id)}
    for modele, champ, ids, statut, libelle in (
        (TicketTransport, TicketTransport.ligne_id, lignes, StatutTicket.REMBOURSE, "Ticket de transport"),
        (TicketCantine, TicketCantine.type_repas_id, repas, StatutTicket.REMBOURSE, "Ticket de cantine"),
        (BilletEvenement, BilletEvenement.evenement_id, set(evenements), StatutBillet.REMBOURSE, "Billet"),
    ):
        if ids:
            for r in db.query(modele).filter(champ.in_(list(ids)), modele.statut == statut, modele.paiement_confirme.is_(True),
                                             modele.remboursement_effectue.is_(False)):
                manuels.append(Element(id=r.id, libelle=libelle, montant=r.prix_paye, detail=_nom(db.get(Utilisateur, r.utilisateur_id))))
    for t in transactions.values():
        if t.statut == StatutTransactionMarketplace.REMBOURSEE and t.paiement_confirme and not t.remboursement_effectue:
            manuels.append(Element(id=t.id, libelle="Achat marketplace", montant=t.prix_paye, detail=_nom(db.get(Utilisateur, t.acheteur_id))))
    sections.append(_section(
        "remboursements", "Remboursements à faire à la main", "Kkiapay n'a pas pu rembourser automatiquement ces paiements.", manuels,
    ))

    # Alertes El Professor
    alertes = db.query(AlerteElProfessor).filter(AlerteElProfessor.etablissement_id == etab_id, AlerteElProfessor.traite.is_(False)).all()
    sections.append(_section(
        "alertes", "Alertes de sécurité El Professor", "Signaux de danger détectés dans une conversation : à traiter par une personne, sans délai.",
        [Element(id=a.id, libelle=a.motif[:160], detail=a.origine.value, ia_niveau="elevee") for a in alertes], urgent=True,
    ))
    return sections


def _sections_ministere(db: Session) -> list[Section | None]:
    sections: list[Section | None] = []
    litiges = db.query(ContestationMicroJob).filter(ContestationMicroJob.statut == StatutContestationMicroJob.EN_ATTENTE).all()
    missions = {m.id: m for m in db.query(MissionMicroJob).filter(MissionMicroJob.id.in_([c.mission_id for c in litiges]))} if litiges else {}
    offres = {o.id: o for o in db.query(OffreMicroJob).filter(OffreMicroJob.id.in_([m.offre_id for m in missions.values()]))} if missions else {}
    sections.append(_section(
        "litiges_micro_jobs", "Litiges de micro-jobs", "Avis de l'IA joint ; un remboursement accordé est versé automatiquement par Kkiapay.",
        [Element(id=c.id, libelle=offres[missions[c.mission_id].offre_id].titre, detail=c.motif, ia=c.ia_justification,
                 ia_niveau=c.ia_decision, montant=missions[c.mission_id].prix_paye) for c in litiges],
    ))
    a_payer = db.query(MissionMicroJob).filter(
        MissionMicroJob.statut == StatutMissionMicroJob.VALIDEE, MissionMicroJob.reference_paiement_prestataire.is_(None)
    ).all()
    prestataires = {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_({m.prestataire_id for m in a_payer}))} if a_payer else {}
    offres_payer = {o.id: o for o in db.query(OffreMicroJob).filter(OffreMicroJob.id.in_({m.offre_id for m in a_payer}))} if a_payer else {}
    sections.append(_section(
        "reversements_micro_jobs", "Missions à payer aux prestataires",
        "Regroupées par étudiant : un seul virement Mobile Money et une seule référence pour toutes ses missions.",
        [Element(id=m.id, libelle=offres_payer[m.offre_id].titre, montant=m.prix_paye, groupe=m.prestataire_id,
                 detail=f"{_nom(prestataires[m.prestataire_id])} — {prestataires[m.prestataire_id].telephone or 'numéro Mobile Money non renseigné'}")
         for m in a_payer],
    ))
    manuels = [Element(id=m.id, libelle="Mission micro-job", montant=m.prix_paye) for m in db.query(MissionMicroJob).filter(
        MissionMicroJob.statut == StatutMissionMicroJob.REMBOURSEE, MissionMicroJob.paiement_confirme.is_(True),
        MissionMicroJob.remboursement_effectue.is_(False))]
    sections.append(_section("remboursements", "Remboursements à faire à la main", "Kkiapay n'a pas pu rembourser automatiquement ces paiements.", manuels))
    propositions = db.query(ReferentielCoefficient).filter(ReferentielCoefficient.statut == StatutReferentiel.PROPOSITION_EN_ATTENTE).all()
    sections.append(_section(
        "referentiels", "Propositions de coefficients", "Validez-les en lot depuis l'écran Référentiels.",
        [Element(id=r.id, libelle=f"{r.niveau} — {r.matiere}", detail=f"coefficient proposé : {r.coefficient:g}") for r in propositions],
    ))
    return sections


@router.get("/administration/a-traiter", response_model=list[Section])
def a_traiter(
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[Section]:
    if admin.role == RoleUtilisateur.ADMIN_MINISTERIEL:
        sections = _sections_ministere(db)
    else:
        lien = db.get(AdminEtablissement, admin.id)
        sections = _sections_etablissement(db, lien.etablissement_id) if lien else []
    resultat = [s for s in sections if s is not None]
    return sorted(resultat, key=lambda s: (not s.urgent,))


class RemboursementsManuelsRequest(BaseModel):
    ids: list[str]


@router.post("/administration/remboursements/effectues", response_model=list[str])
def marquer_remboursements_effectues(
    payload: RemboursementsManuelsRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[str]:
    """Remboursements faits a la main (Kkiapay avait echoue) : l'administrateur confirme,
    ils quittent la boite « A traiter ». Seulement ceux de son perimetre."""
    if admin.role == RoleUtilisateur.ADMIN_MINISTERIEL:
        permis = {e.id for s in _sections_ministere(db) if s and s.cle == "remboursements" for e in s.elements}
    else:
        lien = db.get(AdminEtablissement, admin.id)
        sections = _sections_etablissement(db, lien.etablissement_id) if lien else []
        permis = {e.id for s in sections if s and s.cle == "remboursements" for e in s.elements}
    marques = []
    for modele in (TicketTransport, TicketCantine, BilletEvenement, TransactionMarketplace, MissionMicroJob):
        for ressource in db.query(modele).filter(modele.id.in_([i for i in payload.ids if i in permis])):
            ressource.remboursement_effectue = True
            marques.append(ressource.id)
    db.commit()
    return marques
