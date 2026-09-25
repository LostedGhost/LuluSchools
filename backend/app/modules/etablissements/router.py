from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, get_current_user, require_roles
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.security import generate_temporary_password, hash_password
from app.modules.etablissements.models import AdminEtablissement, Classe, Etablissement
from app.modules.etablissements.schemas import (
    ClasseCreate,
    ClasseOut,
    EtablissementCreate,
    EtablissementOut,
)
from app.modules.identite.models import RoleUtilisateur, Utilisateur

router = APIRouter(prefix="/etablissements", tags=["etablissements"])


def _generer_code_etablissement(db: Session, type_etablissement: str) -> str:
    nombre_existant = (
        db.query(func.count(Etablissement.id)).filter(Etablissement.type == type_etablissement).scalar()
    )
    return f"{type_etablissement}{nombre_existant + 1:02d}"


@router.post("", response_model=EtablissementOut, status_code=status.HTTP_201_CREATED)
def creer_etablissement(
    payload: EtablissementCreate,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
    _admin_ministeriel: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Etablissement:
    email_admin = payload.admin.email.lower()
    if db.query(Utilisateur).filter(Utilisateur.login_id == email_admin).first() is not None:
        raise api_error(
            status.HTTP_409_CONFLICT, "email_deja_utilise", "Un compte existe deja avec cet e-mail."
        )

    etablissement = Etablissement(
        nom=payload.nom,
        type=payload.type,
        statut=payload.statut,
        code_etablissement=_generer_code_etablissement(db, payload.type.value),
    )
    db.add(etablissement)
    db.flush()

    mot_de_passe_temporaire = generate_temporary_password()
    admin_utilisateur = Utilisateur(
        nom=payload.admin.nom,
        prenom=payload.admin.prenom,
        login_id=email_admin,
        email=email_admin,
        mot_de_passe_hash=hash_password(mot_de_passe_temporaire),
        mot_de_passe_temporaire=True,
        role=RoleUtilisateur.ADMIN_ETABLISSEMENT,
        email_verifie=True,
    )
    db.add(admin_utilisateur)
    db.flush()
    db.add(AdminEtablissement(utilisateur_id=admin_utilisateur.id, etablissement_id=etablissement.id))

    try:
        email_client.send_temporary_credentials_email(
            to_email=email_admin,
            to_name=payload.admin.prenom,
            login_id=email_admin,
            mot_de_passe=mot_de_passe_temporaire,
        )
    except EmailDeliveryError as exc:
        db.rollback()
        raise api_error(
            status.HTTP_502_BAD_GATEWAY,
            "envoi_email_echoue",
            "Impossible d'envoyer les identifiants a l'administrateur, veuillez reessayer.",
        ) from exc

    db.commit()
    db.refresh(etablissement)
    return etablissement


@router.get("", response_model=list[EtablissementOut])
def lister_etablissements(
    db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(get_current_user)
) -> list[Etablissement]:
    return db.query(Etablissement).all()


@router.get("/mon-etablissement", response_model=EtablissementOut)
def mon_etablissement(
    db: Session = Depends(get_db), admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT))
) -> Etablissement:
    """Point d'entree du frontend A+ : sans lui, un admin d'etablissement n'a aucun moyen
    de savoir quel etablissement il administre (pas expose sur MeOut)."""
    lien = db.get(AdminEtablissement, admin.id)
    if lien is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Aucun etablissement rattache a ce compte.")
    etablissement = db.get(Etablissement, lien.etablissement_id)
    if etablissement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    return etablissement


@router.get("/{etablissement_id}", response_model=EtablissementOut)
def obtenir_etablissement(
    etablissement_id: str,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(get_current_user),
) -> Etablissement:
    etablissement = db.get(Etablissement, etablissement_id)
    if etablissement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    return etablissement


def _verifier_admin_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    if utilisateur.role != RoleUtilisateur.ADMIN_ETABLISSEMENT:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action.")
    lien = db.get(AdminEtablissement, utilisateur.id)
    if lien is None or lien.etablissement_id != etablissement_id:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "acces_refuse",
            "Vous n'administrez pas cet etablissement.",
        )


@router.post(
    "/{etablissement_id}/classes", response_model=ClasseOut, status_code=status.HTTP_201_CREATED
)
def creer_classe(
    etablissement_id: str,
    payload: ClasseCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> Classe:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)

    classe = Classe(
        etablissement_id=etablissement_id,
        niveau=payload.niveau,
        capacite=payload.capacite,
        politique_depassement=payload.politique_depassement,
    )
    db.add(classe)
    db.commit()
    db.refresh(classe)
    return classe


@router.get("/{etablissement_id}/classes", response_model=list[ClasseOut])
def lister_classes(
    etablissement_id: str,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(get_current_user),
) -> list[Classe]:
    return db.query(Classe).filter(Classe.etablissement_id == etablissement_id).all()
