from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.coffre_fort.models import (
    AlerteDepassementPlafond,
    ModuleDepenseCoffreFort,
    PlafondFamilial,
    StatutValidationParentale,
    ValidationParentale,
)
from app.modules.inscriptions.models import Eleve
from app.modules.marketplace.models import AnnonceMarketplace, StatutTransactionMarketplace, TransactionMarketplace
from app.modules.micro_jobs.models import MissionMicroJob, OffreMicroJob, StatutMissionMicroJob, StatutOffreMicroJob


def _aware_utc(moment: datetime) -> datetime:
    """SQLite (tests) ne conserve pas le fuseau horaire des colonnes DateTime(timezone=True)."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _debut_semaine_courante() -> datetime:
    maintenant = datetime.now(timezone.utc)
    lundi = maintenant.date() - timedelta(days=maintenant.weekday())
    return datetime.combine(lundi, time.min, tzinfo=timezone.utc)


def _depense_semaine_en_cours(db: Session, eleve_utilisateur_id: str) -> float:
    """UC-35.1/35.2 : cumul des depenses de l'enfant (client micro-jobs, acheteur
    marketplace, demandes d'actes payantes - hors demandes annulees/remboursees) depuis
    le debut de la semaine calendaire (lundi). Compte les depenses des leur creation
    (avant meme confirmation du paiement), puisque c'est a ce moment - l'amorcage du
    paiement - que la gate est evaluee ; la ressource dont le paiement est en train
    d'etre amorce est deja incluse ici, `evaluer_depense` ne doit donc jamais y rajouter
    son propre montant une deuxieme fois."""
    debut = _debut_semaine_courante()
    total = 0.0

    offres = (
        db.query(OffreMicroJob)
        .filter(
            OffreMicroJob.client_id == eleve_utilisateur_id,
            OffreMicroJob.statut != StatutOffreMicroJob.ANNULEE,
        )
        .all()
    )
    total += sum(o.prix for o in offres if _aware_utc(o.created_at) >= debut)

    transactions = (
        db.query(TransactionMarketplace)
        .filter(
            TransactionMarketplace.acheteur_id == eleve_utilisateur_id,
            TransactionMarketplace.statut.notin_(
                [StatutTransactionMarketplace.ANNULEE, StatutTransactionMarketplace.REMBOURSEE]
            ),
        )
        .all()
    )
    total += sum(t.prix_paye for t in transactions if _aware_utc(t.created_at) >= debut)

    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is not None:
        demandes = (
            db.query(DemandeActeAcademique)
            .filter(
                DemandeActeAcademique.eleve_id == eleve.id,
                DemandeActeAcademique.statut != StatutDemandeActe.REJETEE,
                DemandeActeAcademique.type_acte_id.isnot(None),
            )
            .all()
        )
        for demande in demandes:
            if _aware_utc(demande.created_at) < debut:
                continue
            type_acte = db.get(TypeActeAcademique, demande.type_acte_id)
            total += type_acte.prix if type_acte is not None else 0.0

    return total


def evaluer_depense(
    db: Session,
    *,
    tuteur_id: str,
    eleve_utilisateur_id: str,
    module: ModuleDepenseCoffreFort,
    reference_id: str,
    montant: float,
) -> ValidationParentale | None:
    """UC-35.1/35.2 : a appeler juste avant d'amorcer le paiement d'une depense de
    l'enfant (offre micro-job, reservation marketplace, demande d'acte). Retourne une
    ValidationParentale EN_ATTENTE si le paiement doit rester bloque jusqu'a decision du
    tuteur, sinon None (le paiement peut continuer normalement). Opt-in strict (UC-35.4) :
    sans PlafondFamilial configure pour cet enfant, ne fait jamais rien."""
    plafond = db.query(PlafondFamilial).filter(PlafondFamilial.eleve_utilisateur_id == eleve_utilisateur_id).first()
    if plafond is None:
        return None

    deja_approuvee = (
        db.query(ValidationParentale)
        .filter(
            ValidationParentale.reference_id == reference_id,
            ValidationParentale.module == module,
            ValidationParentale.statut == StatutValidationParentale.APPROUVEE,
        )
        .first()
    )
    if deja_approuvee is not None:
        return None

    if plafond.seuil_validation is not None and montant > plafond.seuil_validation:
        en_attente = (
            db.query(ValidationParentale)
            .filter(
                ValidationParentale.reference_id == reference_id,
                ValidationParentale.module == module,
                ValidationParentale.statut == StatutValidationParentale.EN_ATTENTE,
            )
            .first()
        )
        if en_attente is None:
            en_attente = ValidationParentale(
                tuteur_id=tuteur_id,
                eleve_utilisateur_id=eleve_utilisateur_id,
                module=module,
                reference_id=reference_id,
                montant=montant,
            )
            db.add(en_attente)
            db.commit()
            db.refresh(en_attente)
        return en_attente

    if plafond.plafond_hebdomadaire is not None:
        depense_semaine = _depense_semaine_en_cours(db, eleve_utilisateur_id)
        if depense_semaine > plafond.plafond_hebdomadaire:
            db.add(
                AlerteDepassementPlafond(
                    tuteur_id=tuteur_id,
                    eleve_utilisateur_id=eleve_utilisateur_id,
                    module=module,
                    montant_semaine=depense_semaine,
                    plafond=plafond.plafond_hebdomadaire,
                )
            )
            db.commit()

    return None


def construire_releve_financier(
    db: Session, eleve_utilisateur_id: str, *, debut: date | None, fin: date | None
) -> dict:
    """UC-35.3 : lecture seule, zero ecriture. `gains_micro_jobs` reste structurellement a
    0 pour un Eleve tant que la regle metier actuelle (Eleve exclu du role PRESTATAIRE,
    voir OffreMicroJob docstring) n'evolue pas - le champ existe pour rester correct si
    cette regle change, et pour couvrir un Tuteur consultant son propre releve."""
    debut_dt = _aware_utc(datetime.combine(debut, time.min, tzinfo=timezone.utc)) if debut else None
    fin_dt = _aware_utc(datetime.combine(fin, time.max, tzinfo=timezone.utc)) if fin else None

    def _dans_la_periode(moment: datetime) -> bool:
        moment = _aware_utc(moment)
        if debut_dt is not None and moment < debut_dt:
            return False
        if fin_dt is not None and moment > fin_dt:
            return False
        return True

    gains_micro_jobs = sum(
        m.prix_paye
        for m in db.query(MissionMicroJob)
        .filter(MissionMicroJob.prestataire_id == eleve_utilisateur_id, MissionMicroJob.statut == StatutMissionMicroJob.PAYEE)
        .all()
        if _dans_la_periode(m.created_at)
    )

    depenses_micro_jobs = sum(
        o.prix
        for o in db.query(OffreMicroJob)
        .filter(OffreMicroJob.client_id == eleve_utilisateur_id, OffreMicroJob.paiement_confirme.is_(True))
        .all()
        if _dans_la_periode(o.created_at)
    )

    ventes_marketplace = sum(
        t.prix_paye
        for t in db.query(TransactionMarketplace)
        .join(AnnonceMarketplace, TransactionMarketplace.annonce_id == AnnonceMarketplace.id)
        .filter(
            AnnonceMarketplace.vendeur_id == eleve_utilisateur_id,
            TransactionMarketplace.statut == StatutTransactionMarketplace.FINALISEE,
        )
        .all()
        if _dans_la_periode(t.created_at)
    )

    achats_marketplace = sum(
        t.prix_paye
        for t in db.query(TransactionMarketplace)
        .filter(
            TransactionMarketplace.acheteur_id == eleve_utilisateur_id,
            TransactionMarketplace.statut == StatutTransactionMarketplace.FINALISEE,
        )
        .all()
        if _dans_la_periode(t.created_at)
    )

    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    frais_actes = 0.0
    if eleve is not None:
        demandes = (
            db.query(DemandeActeAcademique)
            .filter(DemandeActeAcademique.eleve_id == eleve.id, DemandeActeAcademique.paiement_confirme.is_(True))
            .all()
        )
        for demande in demandes:
            if not _dans_la_periode(demande.created_at):
                continue
            type_acte = db.get(TypeActeAcademique, demande.type_acte_id) if demande.type_acte_id else None
            frais_actes += type_acte.prix if type_acte is not None else 0.0

    solde_net = gains_micro_jobs + ventes_marketplace - achats_marketplace - depenses_micro_jobs - frais_actes

    return {
        "eleve_utilisateur_id": eleve_utilisateur_id,
        "periode_debut": debut,
        "periode_fin": fin,
        "gains_micro_jobs": gains_micro_jobs,
        "ventes_marketplace": ventes_marketplace,
        "achats_marketplace": achats_marketplace,
        "depenses_micro_jobs": depenses_micro_jobs,
        "frais_actes": frais_actes,
        "solde_net": solde_net,
    }
