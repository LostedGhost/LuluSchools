from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.actes.schemas import (
    DemandeActeCreate,
    DemandeActeOut,
    PaiementWebhookRequest,
    TraiterDemandeRequest,
    TypeActeCreate,
    TypeActeOut,
)
from app.modules.etablissements.models import AdminEtablissement, Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription

router = APIRouter(tags=["actes"])


def _verifier_admin_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    if utilisateur.role != RoleUtilisateur.ADMIN_ETABLISSEMENT:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action.")
    lien = db.get(AdminEtablissement, utilisateur.id)
    if lien is None or lien.etablissement_id != etablissement_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")


def _etablissement_actuel_de_l_eleve(db: Session, eleve: Eleve) -> str:
    inscription = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )
    if inscription is None:
        raise api_error(
            status.HTTP_409_CONFLICT, "aucune_inscription_validee", "Aucune inscription validee pour cet eleve."
        )
    from app.modules.etablissements.models import Classe

    classe = db.get(Classe, inscription.classe_id)
    return classe.etablissement_id


@router.post(
    "/etablissements/{etablissement_id}/types-actes", response_model=TypeActeOut, status_code=status.HTTP_201_CREATED
)
def creer_type_acte(
    etablissement_id: str,
    payload: TypeActeCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> TypeActeAcademique:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_admin_de_l_etablissement(db, admin, etablissement_id)

    type_acte = TypeActeAcademique(
        etablissement_id=etablissement_id,
        nom=payload.nom,
        prix=payload.prix,
        pieces_requises=payload.pieces_requises,
        condition_eligibilite=payload.condition_eligibilite,
    )
    db.add(type_acte)
    db.commit()
    db.refresh(type_acte)
    return type_acte


@router.get("/etablissements/{etablissement_id}/types-actes", response_model=list[TypeActeOut])
def lister_types_actes(
    etablissement_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(require_roles(
        RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR, RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ADMIN_ETABLISSEMENT
    ))
) -> list[TypeActeAcademique]:
    return db.query(TypeActeAcademique).filter(TypeActeAcademique.etablissement_id == etablissement_id).all()


@router.post("/demandes-actes", response_model=DemandeActeOut, status_code=status.HTTP_201_CREATED)
def soumettre_demande_acte(
    payload: DemandeActeCreate,
    db: Session = Depends(get_db),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> DemandeActeAcademique:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur.id).first()
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Compte eleve introuvable.")

    statut_initial = StatutDemandeActe.EN_TRAITEMENT
    paiement_confirme = True
    if payload.type_acte_id:
        type_acte = db.get(TypeActeAcademique, payload.type_acte_id)
        if type_acte is None:
            raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Type d'acte introuvable.")
        if type_acte.prix > 0:
            statut_initial = StatutDemandeActe.SOUMISE
            paiement_confirme = False

    demande = DemandeActeAcademique(
        eleve_id=eleve.id,
        type_acte_id=payload.type_acte_id,
        est_reclamation=payload.est_reclamation,
        reference_evaluation=payload.reference_evaluation,
        motif=payload.motif,
        statut=statut_initial,
        paiement_confirme=paiement_confirme,
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)
    return demande


@router.post("/demandes-actes/{demande_id}/paiement/webhook", response_model=DemandeActeOut)
def confirmer_paiement(
    demande_id: str, _payload: PaiementWebhookRequest, db: Session = Depends(get_db)
) -> DemandeActeAcademique:
    """Public (webhook Kkiapay). L'integration Kkiapay elle-meme (verification de
    signature, appel reel a l'API) n'est pas construite - ce endpoint pose seulement la
    forme de la confirmation de paiement, a completer avant mise en production."""
    demande = db.get(DemandeActeAcademique, demande_id)
    if demande is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    if demande.statut != StatutDemandeActe.SOUMISE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette demande n'attend pas de paiement.")

    demande.paiement_confirme = True
    demande.statut = StatutDemandeActe.EN_TRAITEMENT
    db.commit()
    db.refresh(demande)
    return demande


@router.get("/demandes-actes/{demande_id}", response_model=DemandeActeOut)
def obtenir_demande_acte(
    demande_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(
        RoleUtilisateur.ELEVE, RoleUtilisateur.ADMIN_ETABLISSEMENT
    ))
) -> DemandeActeAcademique:
    demande = db.get(DemandeActeAcademique, demande_id)
    if demande is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    eleve = db.get(Eleve, demande.eleve_id)

    if utilisateur.role == RoleUtilisateur.ELEVE and eleve.utilisateur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette demande ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        etablissement_id = _etablissement_actuel_de_l_eleve(db, eleve)
        _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)

    return demande


@router.post("/demandes-actes/{demande_id}/traiter", response_model=DemandeActeOut)
def traiter_demande_acte(
    demande_id: str,
    payload: TraiterDemandeRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> DemandeActeAcademique:
    demande = db.get(DemandeActeAcademique, demande_id)
    if demande is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    eleve = db.get(Eleve, demande.eleve_id)
    etablissement_id = _etablissement_actuel_de_l_eleve(db, eleve)
    _verifier_admin_de_l_etablissement(db, admin, etablissement_id)

    if demande.statut != StatutDemandeActe.EN_TRAITEMENT:
        raise api_error(
            status.HTTP_409_CONFLICT, "statut_invalide", "Cette demande n'est pas prete a etre traitee (paiement manquant ?)."
        )
    if payload.decision == StatutDemandeActe.REJETEE and not payload.motif_rejet:
        raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "motif_requis", "Un motif est requis en cas de rejet.")

    demande.statut = payload.decision
    demande.motif_rejet = payload.motif_rejet
    db.commit()
    db.refresh(demande)
    return demande
