from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, require_roles
from app.modules.billetterie.models import BilletEvenement, Evenement, StatutBillet, StatutEvenement
from app.modules.billetterie.schemas import (
    BilletEvenementOut,
    DesignerParrainRequest,
    EvenementCreate,
    EvenementOut,
)
from app.modules.controle_acces.models import ServiceControle
from app.modules.controle_acces.router import est_controleur_designe, verifier_admin_de_l_etablissement
from app.modules.etablissements.models import AdminEtablissement, Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.paiements.schemas import AmorcerPaiementRequest

router = APIRouter(tags=["billetterie"])

_DELAI_REMBOURSEMENT_BILLET = timedelta(hours=48)


def _aware_utc(moment: datetime) -> datetime:
    """SQLite (utilise en test) ne conserve pas l'information de fuseau horaire des
    colonnes DateTime(timezone=True) - les valeurs relues sont naives. Toutes les dates
    du projet sont deja stockees en UTC (voir _utcnow() dans chaque module), donc les
    considerer comme UTC quand l'info est manquante est correct et pas une supposition."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _est_organisateur(db: Session, utilisateur: Utilisateur, evenement: Evenement) -> bool:
    if utilisateur.id == evenement.parrain_utilisateur_id:
        return True
    if utilisateur.role != RoleUtilisateur.ADMIN_ETABLISSEMENT:
        return False
    lien = db.get(AdminEtablissement, utilisateur.id)
    return lien is not None and lien.etablissement_id == evenement.etablissement_id


def _exiger_organisateur(db: Session, utilisateur: Utilisateur, evenement: Evenement) -> None:
    if not _est_organisateur(db, utilisateur, evenement):
        raise api_error(
            status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'organisez pas cet evenement."
        )


@router.post(
    "/etablissements/{etablissement_id}/evenements", response_model=EvenementOut, status_code=status.HTTP_201_CREATED
)
def creer_evenement(
    etablissement_id: str,
    payload: EvenementCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> Evenement:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)

    evenement = Evenement(
        etablissement_id=etablissement_id,
        titre=payload.titre,
        description=payload.description,
        lieu=payload.lieu,
        date_heure=payload.date_heure,
        capacite_max=payload.capacite_max,
        prix_billet=payload.prix_billet,
    )
    db.add(evenement)
    db.commit()
    db.refresh(evenement)
    return evenement


@router.post("/evenements/{evenement_id}/parrain", response_model=EvenementOut)
def designer_parrain(
    evenement_id: str,
    payload: DesignerParrainRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> Evenement:
    evenement = db.get(Evenement, evenement_id)
    if evenement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Evenement introuvable.")
    verifier_admin_de_l_etablissement(db, admin, evenement.etablissement_id)
    if db.get(Utilisateur, payload.utilisateur_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Utilisateur a designer introuvable.")

    evenement.parrain_utilisateur_id = payload.utilisateur_id
    db.commit()
    db.refresh(evenement)
    return evenement


@router.get("/etablissements/{etablissement_id}/evenements", response_model=list[EvenementOut])
def lister_evenements(
    etablissement_id: str,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(get_current_active_user),
) -> list[Evenement]:
    return db.query(Evenement).filter(Evenement.etablissement_id == etablissement_id).all()


@router.get("/evenements/{evenement_id}", response_model=EvenementOut)
def obtenir_evenement(
    evenement_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(get_current_active_user)
) -> Evenement:
    evenement = db.get(Evenement, evenement_id)
    if evenement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Evenement introuvable.")
    return evenement


@router.post("/evenements/{evenement_id}/annuler", response_model=EvenementOut)
def annuler_evenement(
    evenement_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> Evenement:
    evenement = db.get(Evenement, evenement_id)
    if evenement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Evenement introuvable.")
    _exiger_organisateur(db, utilisateur, evenement)
    if evenement.statut != StatutEvenement.OUVERT:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cet evenement n'est plus ouvert.")

    evenement.statut = StatutEvenement.ANNULE
    billets_a_rembourser = (
        db.query(BilletEvenement)
        .filter(
            BilletEvenement.evenement_id == evenement_id,
            BilletEvenement.statut.in_([StatutBillet.ACHETE, StatutBillet.VALIDE]),
        )
        .all()
    )
    for billet in billets_a_rembourser:
        billet.statut = StatutBillet.REMBOURSE
    db.commit()
    db.refresh(evenement)
    return evenement


@router.post(
    "/evenements/{evenement_id}/billets", response_model=BilletEvenementOut, status_code=status.HTTP_201_CREATED
)
def acheter_billet(
    evenement_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> BilletEvenement:
    evenement = db.get(Evenement, evenement_id)
    if evenement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Evenement introuvable.")
    if evenement.statut != StatutEvenement.OUVERT:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cet evenement n'accepte plus d'achats.")

    deja_vendus = (
        db.query(BilletEvenement)
        .filter(
            BilletEvenement.evenement_id == evenement_id,
            BilletEvenement.statut.in_([StatutBillet.ACHETE, StatutBillet.VALIDE]),
        )
        .count()
    )
    if deja_vendus >= evenement.capacite_max:
        raise api_error(status.HTTP_409_CONFLICT, "capacite_atteinte", "Cet evenement est complet.")

    billet = BilletEvenement(
        evenement_id=evenement_id,
        utilisateur_id=utilisateur.id,
        prix_paye=evenement.prix_billet,
        paiement_confirme=evenement.prix_billet == 0,
    )
    db.add(billet)
    db.commit()
    db.refresh(billet)
    return billet


@router.post("/billets/{billet_id}/paiement/amorcer", response_model=BilletEvenementOut)
def amorcer_paiement_billet(
    billet_id: str,
    payload: AmorcerPaiementRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> BilletEvenement:
    billet = db.get(BilletEvenement, billet_id)
    if billet is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Billet introuvable.")
    if billet.utilisateur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce billet ne vous appartient pas.")
    if billet.statut != StatutBillet.ACHETE or billet.paiement_confirme:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce billet n'attend pas de paiement.")

    billet.kkiapay_transaction_id = payload.transaction_id
    db.commit()
    db.refresh(billet)
    return billet


@router.post("/billets/{billet_id}/valider", response_model=BilletEvenementOut)
def valider_billet(
    billet_id: str, db: Session = Depends(get_db), controleur: Utilisateur = Depends(get_current_active_user)
) -> BilletEvenement:
    billet = db.get(BilletEvenement, billet_id)
    if billet is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Billet introuvable.")
    evenement = db.get(Evenement, billet.evenement_id)
    if not est_controleur_designe(
        db, controleur.id, evenement.etablissement_id, ServiceControle.EVENEMENT, evenement.id
    ):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas controleur designe pour cet evenement.")
    if billet.statut != StatutBillet.ACHETE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce billet ne peut pas etre valide.")
    if not billet.paiement_confirme:
        raise api_error(status.HTTP_409_CONFLICT, "paiement_non_confirme", "Le paiement de ce billet n'est pas confirme.")

    billet.statut = StatutBillet.VALIDE
    db.commit()
    db.refresh(billet)
    return billet


@router.post("/billets/{billet_id}/rembourser", response_model=BilletEvenementOut)
def rembourser_billet(
    billet_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> BilletEvenement:
    billet = db.get(BilletEvenement, billet_id)
    if billet is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Billet introuvable.")
    if billet.utilisateur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce billet ne vous appartient pas.")
    if billet.statut != StatutBillet.ACHETE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce billet ne peut plus etre rembourse.")
    evenement = db.get(Evenement, billet.evenement_id)
    if datetime.now(timezone.utc) > _aware_utc(evenement.date_heure) - _DELAI_REMBOURSEMENT_BILLET:
        raise api_error(status.HTTP_409_CONFLICT, "delai_depasse", "Le delai de remboursement est depasse.")

    billet.statut = StatutBillet.REMBOURSE
    db.commit()
    db.refresh(billet)
    return billet


@router.get("/mes-billets", response_model=list[BilletEvenementOut])
def mes_billets(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> list[BilletEvenement]:
    return (
        db.query(BilletEvenement)
        .filter(BilletEvenement.utilisateur_id == utilisateur.id)
        .order_by(BilletEvenement.created_at.desc())
        .all()
    )
