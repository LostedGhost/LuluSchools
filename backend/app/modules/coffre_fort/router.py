from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.modules.coffre_fort.models import AlerteDepassementPlafond, PlafondFamilial, StatutValidationParentale, ValidationParentale
from app.modules.coffre_fort.schemas import (
    AlerteDepassementPlafondOut,
    DecisionValidationParentaleRequest,
    PlafondFamilialOut,
    PlafondFamilialUpsert,
    ReleveFinancierOut,
    ValidationParentaleOut,
)
from app.modules.coffre_fort.service import construire_releve_financier
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve

router = APIRouter(tags=["coffre-fort"])


def _verifier_tuteur_de_l_eleve(db: Session, tuteur: Utilisateur, eleve_utilisateur_id: str) -> None:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None or eleve.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte tuteur.")


@router.put("/mes-enfants/{eleve_utilisateur_id}/coffre-fort/plafond", response_model=PlafondFamilialOut)
def definir_plafond_familial(
    eleve_utilisateur_id: str,
    payload: PlafondFamilialUpsert,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> PlafondFamilial:
    """UC-35.1 : opt-in strict, cree ou met a jour la configuration en une seule
    operation (un seul PlafondFamilial par enfant)."""
    _verifier_tuteur_de_l_eleve(db, utilisateur, eleve_utilisateur_id)
    plafond = (
        db.query(PlafondFamilial).filter(PlafondFamilial.eleve_utilisateur_id == eleve_utilisateur_id).first()
    )
    if plafond is None:
        plafond = PlafondFamilial(tuteur_id=utilisateur.id, eleve_utilisateur_id=eleve_utilisateur_id)
        db.add(plafond)
    plafond.plafond_hebdomadaire = payload.plafond_hebdomadaire
    plafond.seuil_validation = payload.seuil_validation
    db.commit()
    db.refresh(plafond)
    return plafond


@router.get("/mes-enfants/{eleve_utilisateur_id}/coffre-fort/plafond", response_model=PlafondFamilialOut | None)
def obtenir_plafond_familial(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> PlafondFamilial | None:
    _verifier_tuteur_de_l_eleve(db, utilisateur, eleve_utilisateur_id)
    return db.query(PlafondFamilial).filter(PlafondFamilial.eleve_utilisateur_id == eleve_utilisateur_id).first()


@router.get("/mes-enfants/{eleve_utilisateur_id}/coffre-fort/releve", response_model=ReleveFinancierOut)
def obtenir_releve_financier(
    eleve_utilisateur_id: str,
    debut: date | None = Query(default=None),
    fin: date | None = Query(default=None),
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> dict:
    """UC-35.3 : lecture seule, disponible meme sans PlafondFamilial configure."""
    _verifier_tuteur_de_l_eleve(db, utilisateur, eleve_utilisateur_id)
    return construire_releve_financier(db, eleve_utilisateur_id, debut=debut, fin=fin)


@router.get(
    "/mes-enfants/{eleve_utilisateur_id}/coffre-fort/validations-en-attente",
    response_model=list[ValidationParentaleOut],
)
def lister_validations_en_attente(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> list[ValidationParentale]:
    _verifier_tuteur_de_l_eleve(db, utilisateur, eleve_utilisateur_id)
    return (
        db.query(ValidationParentale)
        .filter(
            ValidationParentale.eleve_utilisateur_id == eleve_utilisateur_id,
            ValidationParentale.statut == StatutValidationParentale.EN_ATTENTE,
        )
        .order_by(ValidationParentale.created_at.desc())
        .all()
    )


def _trancher_validation(
    db: Session, utilisateur: Utilisateur, validation_id: str, *, statut: StatutValidationParentale, motif_refus: str | None
) -> ValidationParentale:
    validation = db.get(ValidationParentale, validation_id)
    if validation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Validation parentale introuvable.")
    if validation.tuteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette validation ne vous appartient pas.")
    if validation.statut != StatutValidationParentale.EN_ATTENTE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette validation a deja ete tranchee.")

    validation.statut = statut
    validation.motif_refus = motif_refus
    validation.decidee_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(validation)
    return validation


@router.post("/coffre-fort/validations/{validation_id}/approuver", response_model=ValidationParentaleOut)
def approuver_validation_parentale(
    validation_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> ValidationParentale:
    """UC-35.2 : une fois approuvee, l'enfant peut relancer l'amorcage du paiement de
    la meme offre/reservation/demande - le paiement en lui-meme n'est jamais declenche ici."""
    return _trancher_validation(
        db, utilisateur, validation_id, statut=StatutValidationParentale.APPROUVEE, motif_refus=None
    )


@router.post("/coffre-fort/validations/{validation_id}/refuser", response_model=ValidationParentaleOut)
def refuser_validation_parentale(
    validation_id: str,
    payload: DecisionValidationParentaleRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> ValidationParentale:
    return _trancher_validation(
        db, utilisateur, validation_id, statut=StatutValidationParentale.REFUSEE, motif_refus=payload.motif_refus
    )


@router.get("/mes-enfants/{eleve_utilisateur_id}/coffre-fort/alertes", response_model=list[AlerteDepassementPlafondOut])
def lister_alertes_depassement_plafond(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> list[AlerteDepassementPlafond]:
    _verifier_tuteur_de_l_eleve(db, utilisateur, eleve_utilisateur_id)
    return (
        db.query(AlerteDepassementPlafond)
        .filter(AlerteDepassementPlafond.eleve_utilisateur_id == eleve_utilisateur_id)
        .order_by(AlerteDepassementPlafond.created_at.desc())
        .all()
    )


@router.get("/coffre-fort/mes-validations-en-attente", response_model=list[ValidationParentaleOut])
def mes_validations_en_attente(
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> list[ValidationParentale]:
    """UC-35.2 : "jamais un blocage silencieux" - l'eleve doit pouvoir constater
    lui-meme qu'une de ses depenses attend une validation parentale."""
    return (
        db.query(ValidationParentale)
        .filter(ValidationParentale.eleve_utilisateur_id == utilisateur.id)
        .order_by(ValidationParentale.created_at.desc())
        .all()
    )
