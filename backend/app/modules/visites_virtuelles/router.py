from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, require_roles
from app.modules.controle_acces.router import verifier_admin_de_l_etablissement
from app.modules.etablissements.models import Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.visites_virtuelles.models import VisiteVirtuelle
from app.modules.visites_virtuelles.schemas import VisiteVirtuelleCreate, VisiteVirtuelleOut

router = APIRouter(tags=["visites-virtuelles"])


def _verifier_droit_gestion(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    if utilisateur.role == RoleUtilisateur.ADMIN_MINISTERIEL:
        return
    verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)


@router.post(
    "/etablissements/{etablissement_id}/visites-virtuelles",
    response_model=VisiteVirtuelleOut,
    status_code=status.HTTP_201_CREATED,
)
def publier_visite_virtuelle(
    etablissement_id: str,
    payload: VisiteVirtuelleCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    ),
) -> VisiteVirtuelle:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_droit_gestion(db, utilisateur, etablissement_id)

    visite = VisiteVirtuelle(
        etablissement_id=etablissement_id,
        type=payload.type,
        lien_externe=payload.lien_externe,
        attestation_autorisation=payload.attestation_autorisation,
    )
    db.add(visite)
    db.commit()
    db.refresh(visite)
    return visite


@router.get("/etablissements/{etablissement_id}/visites-virtuelles", response_model=list[VisiteVirtuelleOut])
def lister_visites_virtuelles(
    etablissement_id: str,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(get_current_active_user),
) -> list[VisiteVirtuelle]:
    return db.query(VisiteVirtuelle).filter(VisiteVirtuelle.etablissement_id == etablissement_id).all()


@router.delete("/visites-virtuelles/{visite_id}", status_code=status.HTTP_204_NO_CONTENT)
def retirer_visite_virtuelle(
    visite_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    ),
) -> None:
    visite = db.get(VisiteVirtuelle, visite_id)
    if visite is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Visite virtuelle introuvable.")
    _verifier_droit_gestion(db, utilisateur, visite.etablissement_id)
    db.delete(visite)
    db.commit()
