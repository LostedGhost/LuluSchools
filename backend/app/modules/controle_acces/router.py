from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles, verifier_portee_etablissement
from app.modules.controle_acces.models import DesignationControleur, ServiceControle
from app.modules.controle_acces.schemas import DesignationControleurCreate, DesignationControleurOut
from app.modules.etablissements.models import AdminEtablissement, Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur

router = APIRouter(tags=["controle-acces"])


def verifier_admin_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    verifier_portee_etablissement(db, utilisateur, etablissement_id)


def est_controleur_designe(
    db: Session, utilisateur_id: str, etablissement_id: str, service: ServiceControle, evenement_id: str | None = None
) -> bool:
    """Reutilise par services_scolaires et billetterie pour verifier qu'un utilisateur
    est bien le Controleur/Ticketeur designe avant de le laisser valider un ticket/billet."""
    query = db.query(DesignationControleur).filter(
        DesignationControleur.utilisateur_id == utilisateur_id,
        DesignationControleur.etablissement_id == etablissement_id,
        DesignationControleur.service == service,
    )
    if service == ServiceControle.EVENEMENT:
        query = query.filter(DesignationControleur.evenement_id == evenement_id)
    return query.first() is not None


@router.post(
    "/etablissements/{etablissement_id}/controleurs",
    response_model=DesignationControleurOut,
    status_code=status.HTTP_201_CREATED,
)
def designer_controleur(
    etablissement_id: str,
    payload: DesignationControleurCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> DesignationControleur:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)

    if db.get(Utilisateur, payload.utilisateur_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Utilisateur a designer introuvable.")

    designation = DesignationControleur(
        etablissement_id=etablissement_id,
        utilisateur_id=payload.utilisateur_id,
        service=payload.service,
        evenement_id=payload.evenement_id,
    )
    db.add(designation)
    db.commit()
    db.refresh(designation)
    return designation


@router.get(
    "/etablissements/{etablissement_id}/controleurs", response_model=list[DesignationControleurOut]
)
def lister_controleurs(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[DesignationControleur]:
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)
    return (
        db.query(DesignationControleur)
        .filter(DesignationControleur.etablissement_id == etablissement_id)
        .all()
    )


@router.delete("/controleurs/{designation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoquer_controleur(
    designation_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> None:
    designation = db.get(DesignationControleur, designation_id)
    if designation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Designation introuvable.")
    verifier_admin_de_l_etablissement(db, admin, designation.etablissement_id)
    db.delete(designation)
    db.commit()
