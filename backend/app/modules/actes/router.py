from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles, verifier_portee_etablissement
from app.core.files import MO, TYPES_DOCUMENT, FileStorageError, LuluFilesClient, get_files_client, lire_upload_borne
from app.core.formulaire import valider_reponses_formulaire
from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.coffre_fort.models import ModuleDepenseCoffreFort
from app.modules.coffre_fort.service import evaluer_depense
from app.modules.actes.schemas import (
    AmorcerPaiementRequest,
    DemandeActeCreate,
    DemandeActeOut,
    LienDocumentOut,
    TraiterDemandeRequest,
    TypeActeCreate,
    TypeActeOut,
)
from app.modules.etablissements.models import AdminEtablissement, Classe, Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription

router = APIRouter(tags=["actes"])


def _verifier_admin_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    verifier_portee_etablissement(db, utilisateur, etablissement_id)


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
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
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
        schema_formulaire=[c.model_dump() for c in payload.schema_formulaire] if payload.schema_formulaire else None,
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


@router.get("/etablissements/{etablissement_id}/demandes-actes", response_model=list[DemandeActeOut])
def demandes_actes_de_l_etablissement(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[DemandeActeAcademique]:
    """Ecran A+ : sans cette liste, l'admin n'a aucun moyen de decouvrir les demandes
    d'actes/reclamations en attente de traitement pour son etablissement (UC-10)."""
    _verifier_admin_de_l_etablissement(db, admin, etablissement_id)
    classe_ids = db.query(Classe.id).filter(Classe.etablissement_id == etablissement_id)
    eleve_ids = [
        row[0]
        for row in db.query(Inscription.eleve_id).filter(Inscription.classe_id.in_(classe_ids)).distinct().all()
    ]
    if not eleve_ids:
        return []
    return (
        db.query(DemandeActeAcademique)
        .filter(DemandeActeAcademique.eleve_id.in_(eleve_ids), DemandeActeAcademique.statut != StatutDemandeActe.SOUMISE)
        .order_by(DemandeActeAcademique.created_at.asc())
        .all()
    )


@router.get("/mes-demandes-actes", response_model=list[DemandeActeOut])
def mes_demandes_actes(
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> list[DemandeActeAcademique]:
    """Permet a l'eleve ou a son tuteur de retrouver l'historique de ses demandes/
    reclamations sans avoir a garder les identifiants de chaque demande cote client."""
    if utilisateur.role == RoleUtilisateur.ELEVE:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
        eleve_ids = [eleve.id] if eleve is not None else []
    else:
        eleve_ids = [e.id for e in db.query(Eleve).filter(Eleve.tuteur_id == utilisateur.id).all()]

    if not eleve_ids:
        return []
    return (
        db.query(DemandeActeAcademique)
        .filter(DemandeActeAcademique.eleve_id.in_(eleve_ids))
        .order_by(DemandeActeAcademique.created_at.desc())
        .all()
    )


@router.post("/demandes-actes", response_model=DemandeActeOut, status_code=status.HTTP_201_CREATED)
def soumettre_demande_acte(
    payload: DemandeActeCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> DemandeActeAcademique:
    """UC-10 : seuls le titulaire (l'eleve) et ses tuteurs sont habilites a soumettre."""
    if utilisateur.role == RoleUtilisateur.ELEVE:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
    else:
        if not payload.eleve_utilisateur_id:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "eleve_requis", "eleve_utilisateur_id est requis pour un tuteur."
            )
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == payload.eleve_utilisateur_id).first()
        if eleve is not None and eleve.tuteur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte.")
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Compte eleve introuvable.")

    statut_initial = StatutDemandeActe.EN_TRAITEMENT
    paiement_confirme = True
    reponses_validees = None
    if payload.type_acte_id:
        type_acte = db.get(TypeActeAcademique, payload.type_acte_id)
        if type_acte is None:
            raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Type d'acte introuvable.")
        # Sans ce controle, un eleve pouvait choisir le type d'acte (eventuellement gratuit)
        # d'un autre etablissement et contourner les frais fixes par le sien.
        if type_acte.etablissement_id != _etablissement_actuel_de_l_eleve(db, eleve):
            raise api_error(
                status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce type d'acte n'appartient pas a l'etablissement de l'eleve."
            )
        if type_acte.prix > 0:
            statut_initial = StatutDemandeActe.SOUMISE
            paiement_confirme = False
        # UC-51/65 : reponses au schema_formulaire du type d'acte, memes regles que le
        # formulaire de candidature (recrutement/router.py::postuler).
        reponses_validees = valider_reponses_formulaire(type_acte.schema_formulaire, payload.reponses_formulaire)

    demande = DemandeActeAcademique(
        eleve_id=eleve.id,
        type_acte_id=payload.type_acte_id,
        est_reclamation=payload.est_reclamation,
        reference_evaluation=payload.reference_evaluation,
        motif=payload.motif,
        reponses_formulaire=reponses_validees,
        statut=statut_initial,
        paiement_confirme=paiement_confirme,
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)
    return demande


@router.post("/demandes-actes/{demande_id}/paiement/amorcer", response_model=DemandeActeOut)
def amorcer_paiement(
    demande_id: str,
    payload: AmorcerPaiementRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> DemandeActeAcademique:
    """Appele par le client juste apres avoir obtenu un transactionId du widget Kkiapay
    (cote frontend), pour associer cette transaction a la demande AVANT que le webhook
    global ne confirme le paiement (voir POST /paiements/webhook/kkiapay)."""
    demande = db.get(DemandeActeAcademique, demande_id)
    if demande is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    eleve = db.get(Eleve, demande.eleve_id)
    if utilisateur.role == RoleUtilisateur.ELEVE and eleve.utilisateur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette demande ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.TUTEUR and eleve.tuteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette demande ne vous appartient pas.")
    if demande.statut != StatutDemandeActe.SOUMISE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette demande n'attend pas de paiement.")

    if utilisateur.role == RoleUtilisateur.ELEVE and eleve.tuteur_id is not None:
        type_acte = db.get(TypeActeAcademique, demande.type_acte_id) if demande.type_acte_id else None
        montant = type_acte.prix if type_acte is not None else 0.0
        validation = evaluer_depense(
            db,
            tuteur_id=eleve.tuteur_id,
            eleve_utilisateur_id=utilisateur.id,
            module=ModuleDepenseCoffreFort.ACTE,
            reference_id=demande.id,
            montant=montant,
        )
        if validation is not None:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "en_attente_validation_parentale",
                "Cette depense depasse le seuil defini par votre tuteur et attend sa validation.",
            )

    demande.kkiapay_transaction_id = payload.transaction_id
    db.commit()
    db.refresh(demande)
    return demande


@router.get("/demandes-actes/{demande_id}", response_model=DemandeActeOut)
def obtenir_demande_acte(
    demande_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(
        RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR, RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL
    ))
) -> DemandeActeAcademique:
    demande = db.get(DemandeActeAcademique, demande_id)
    if demande is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    eleve = db.get(Eleve, demande.eleve_id)

    if utilisateur.role == RoleUtilisateur.ELEVE and eleve.utilisateur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette demande ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.TUTEUR and eleve.tuteur_id != utilisateur.id:
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
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
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
    if payload.decision not in (StatutDemandeActe.ACCEPTEE, StatutDemandeActe.REJETEE):
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "decision_invalide", "Decision invalide.")
    if payload.decision == StatutDemandeActe.REJETEE and not payload.motif_rejet:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "motif_requis", "Un motif est requis en cas de rejet.")

    demande.statut = payload.decision
    demande.motif_rejet = payload.motif_rejet
    db.commit()
    db.refresh(demande)
    return demande


def _verifier_proprietaire_ou_tuteur(db: Session, utilisateur: Utilisateur, eleve: Eleve) -> None:
    if utilisateur.role == RoleUtilisateur.ELEVE and eleve.utilisateur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette demande ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.TUTEUR and eleve.tuteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette demande ne vous appartient pas.")


@router.post("/demandes-actes/{demande_id}/pieces/{champ_id}", response_model=DemandeActeOut)
def televerser_piece_jointe(
    demande_id: str,
    champ_id: str,
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> DemandeActeAcademique:
    """UC-51/65 : upload d'une piece pour un champ de type "fichier" du
    schema_formulaire - appel dedie APRES la creation de la demande (voir
    valider_reponses_formulaire, qui n'exige jamais un fichier des la creation)."""
    demande = db.get(DemandeActeAcademique, demande_id)
    if demande is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    eleve = db.get(Eleve, demande.eleve_id)
    _verifier_proprietaire_ou_tuteur(db, utilisateur, eleve)

    if demande.statut in (StatutDemandeActe.ACCEPTEE, StatutDemandeActe.REJETEE):
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette demande a deja ete traitee.")
    type_acte = db.get(TypeActeAcademique, demande.type_acte_id) if demande.type_acte_id else None
    champs_fichier = (
        {c["id"] for c in (type_acte.schema_formulaire or []) if c.get("type") == "fichier"} if type_acte else set()
    )
    if champ_id not in champs_fichier:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "champ_inconnu", "Ce champ n'existe pas sur ce type d'acte.")

    contenu = lire_upload_borne(fichier, 10 * MO, TYPES_DOCUMENT)
    try:
        lulufiles_file_id = files_client.upload(
            contenu, fichier.filename or champ_id, fichier.content_type or "application/octet-stream"
        )
    except FileStorageError as exc:
        raise api_error(status.HTTP_502_BAD_GATEWAY, "upload_echoue", "Impossible d'envoyer la piece jointe.") from exc

    demande.reponses_formulaire = {**(demande.reponses_formulaire or {}), champ_id: lulufiles_file_id}
    db.commit()
    db.refresh(demande)
    return demande


@router.post("/demandes-actes/{demande_id}/livrer-document", response_model=DemandeActeOut)
def livrer_document_acte(
    demande_id: str,
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> DemandeActeAcademique:
    """UC-52/66 : resout l'ecart deja documente (aucune livraison de document possible) -
    reserve a l'acte ACCEPTEE, condition de telechargement (UC-53/67)."""
    demande = db.get(DemandeActeAcademique, demande_id)
    if demande is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    eleve = db.get(Eleve, demande.eleve_id)
    etablissement_id = _etablissement_actuel_de_l_eleve(db, eleve)
    _verifier_admin_de_l_etablissement(db, admin, etablissement_id)

    if demande.statut != StatutDemandeActe.ACCEPTEE:
        raise api_error(
            status.HTTP_409_CONFLICT, "statut_invalide", "Seule une demande acceptee peut recevoir son document final."
        )

    contenu = lire_upload_borne(fichier, 20 * MO, TYPES_DOCUMENT)
    try:
        lulufiles_file_id = files_client.upload(
            contenu, fichier.filename or "acte.pdf", fichier.content_type or "application/pdf"
        )
    except FileStorageError as exc:
        raise api_error(status.HTTP_502_BAD_GATEWAY, "upload_echoue", "Impossible d'envoyer le document.") from exc

    demande.document_final_lulufiles_id = lulufiles_file_id
    db.commit()
    db.refresh(demande)
    return demande


@router.get("/demandes-actes/{demande_id}/lien-document", response_model=LienDocumentOut)
def obtenir_lien_document_acte(
    demande_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> LienDocumentOut:
    demande = db.get(DemandeActeAcademique, demande_id)
    if demande is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    eleve = db.get(Eleve, demande.eleve_id)
    _verifier_proprietaire_ou_tuteur(db, utilisateur, eleve)
    if not demande.document_final_lulufiles_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Le document final n'est pas encore disponible.")

    try:
        url = files_client.get_signed_link(demande.document_final_lulufiles_id, disposition="attachment")
    except FileStorageError as exc:
        raise api_error(status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible d'obtenir le lien du document.") from exc
    return LienDocumentOut(url=url)
