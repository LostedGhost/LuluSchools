from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.modules.controle_acces.router import verifier_admin_de_l_etablissement
from app.modules.etablissements.models import Classe, Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.inscriptions.router import AGE_MAJORITE_NUMERIQUE, _age_a
from app.modules.marketplace.models import (
    AnnonceMarketplace,
    CategorieAnnonce,
    ContestationMarketplace,
    EtatArticle,
    PhotoAnnonceMarketplace,
    SignalementAnnonceMarketplace,
    StatutAnnonce,
    StatutContestationMarketplace,
    StatutTransactionMarketplace,
    TransactionMarketplace,
)
from app.modules.marketplace.schemas import (
    AnnonceMarketplaceDetailOut,
    AnnonceMarketplaceOut,
    AnnoncesMarketplacePage,
    ContestationMarketplaceOut,
    ContesterTransactionRequest,
    DecisionContestationMarketplaceRequest,
    PhotoAnnonceLienOut,
    ReverserVendeurRequest,
    RetirerAnnonceRequest,
    SignalementAnnonceOut,
    TraiterSignalementAnnonceRequest,
    TransactionMarketplaceOut,
)
from app.modules.paiements.schemas import AmorcerPaiementRequest

router = APIRouter(tags=["marketplace"])

_DELAI_CONFIRMATION_RECEPTION = timedelta(days=5)

# Transactions dans un statut non termine : bloquent une nouvelle reservation de la
# meme annonce (voir Annonce.statut, deja RESERVEE) et sont celles qu'un retrait
# d'annonce par l'A+ doit resoudre automatiquement (voir retirer_annonce).
_STATUTS_TRANSACTION_EN_COURS = (
    StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT,
    StatutTransactionMarketplace.PAIEMENT_CONFIRME,
    StatutTransactionMarketplace.REMISE_DECLAREE,
    StatutTransactionMarketplace.CONTESTEE,
)


def _aware_utc(moment: datetime) -> datetime:
    """SQLite (tests) ne conserve pas le fuseau horaire des colonnes DateTime(timezone=True)."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _etablissement_actuel_de_l_eleve(db: Session, utilisateur_id: str) -> str | None:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur_id).first()
    if eleve is None:
        return None
    inscription = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )
    if inscription is None:
        return None
    classe = db.get(Classe, inscription.classe_id)
    return classe.etablissement_id if classe else None


def _verifier_eleve_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> Eleve:
    """UC-20 : reserve aux eleves >=16 ans (meme seuil que l'auto-validation
    d'inscription, Art. 446), inscrits et valides dans CET etablissement precis."""
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
    if eleve is None or _age_a(eleve.date_naissance) < AGE_MAJORITE_NUMERIQUE:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "acces_refuse",
            "La marketplace est reservee aux eleves de 16 ans ou plus.",
        )
    if _etablissement_actuel_de_l_eleve(db, utilisateur.id) != etablissement_id:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas inscrit dans cet etablissement."
        )
    return eleve


def _transaction_en_cours(db: Session, annonce_id: str) -> TransactionMarketplace | None:
    return (
        db.query(TransactionMarketplace)
        .filter(
            TransactionMarketplace.annonce_id == annonce_id,
            TransactionMarketplace.statut.in_(_STATUTS_TRANSACTION_EN_COURS),
        )
        .order_by(TransactionMarketplace.created_at.desc())
        .first()
    )


def _appliquer_confirmation_tacite(db: Session, transaction: TransactionMarketplace) -> TransactionMarketplace:
    if (
        transaction.statut == StatutTransactionMarketplace.REMISE_DECLAREE
        and transaction.date_limite_confirmation is not None
        and datetime.now(timezone.utc) > _aware_utc(transaction.date_limite_confirmation)
    ):
        transaction.statut = StatutTransactionMarketplace.CONFIRMEE
        db.commit()
        db.refresh(transaction)
    return transaction


def _serialiser_annonce_detail(
    db: Session, annonce: AnnonceMarketplace, files_client: LuluFilesClient
) -> AnnonceMarketplaceDetailOut:
    photos = (
        db.query(PhotoAnnonceMarketplace)
        .filter(PhotoAnnonceMarketplace.annonce_id == annonce.id)
        .order_by(PhotoAnnonceMarketplace.ordre.asc())
        .all()
    )
    liens: list[PhotoAnnonceLienOut] = []
    for photo in photos:
        try:
            url = files_client.get_signed_link(photo.lulufiles_file_id, disposition="inline")
        except FileStorageError:
            continue
        liens.append(PhotoAnnonceLienOut(id=photo.id, url=url, ordre=photo.ordre))
    base = AnnonceMarketplaceOut.model_validate(annonce)
    return AnnonceMarketplaceDetailOut(**base.model_dump(), photos=liens)


@router.post(
    "/etablissements/{etablissement_id}/marketplace/annonces",
    response_model=AnnonceMarketplaceDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def creer_annonce(
    etablissement_id: str,
    titre: str = Form(...),
    description: str = Form(...),
    categorie: CategorieAnnonce = Form(...),
    etat: EtatArticle = Form(...),
    prix: float = Form(..., gt=0),
    photos: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> AnnonceMarketplaceDetailOut:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_eleve_de_l_etablissement(db, utilisateur, etablissement_id)

    if not photos or not any(p.filename for p in photos):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "photo_requise", "Au moins une photo est obligatoire."
        )

    annonce = AnnonceMarketplace(
        etablissement_id=etablissement_id,
        vendeur_id=utilisateur.id,
        titre=titre,
        description=description,
        categorie=categorie,
        etat=etat,
        prix=prix,
    )
    db.add(annonce)
    db.flush()

    for ordre, fichier in enumerate(photos):
        contenu = await fichier.read()
        try:
            file_id = files_client.upload(
                contenu, fichier.filename or f"photo-{ordre}.jpg", fichier.content_type or "image/jpeg"
            )
        except FileStorageError as exc:
            db.rollback()
            raise api_error(
                status.HTTP_502_BAD_GATEWAY, "upload_echoue", "Impossible d'envoyer une photo, veuillez reessayer."
            ) from exc
        db.add(PhotoAnnonceMarketplace(annonce_id=annonce.id, lulufiles_file_id=file_id, ordre=ordre))

    db.commit()
    db.refresh(annonce)
    return _serialiser_annonce_detail(db, annonce, files_client)


@router.get("/etablissements/{etablissement_id}/marketplace/annonces", response_model=AnnoncesMarketplacePage)
def lister_annonces(
    etablissement_id: str,
    categorie: CategorieAnnonce | None = None,
    etat: EtatArticle | None = None,
    prix_min: float | None = None,
    prix_max: float | None = None,
    statut: StatutAnnonce = StatutAnnonce.DISPONIBLE,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=60),
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> AnnoncesMarketplacePage:
    _verifier_eleve_de_l_etablissement(db, utilisateur, etablissement_id)

    requete = db.query(AnnonceMarketplace).filter(
        AnnonceMarketplace.etablissement_id == etablissement_id, AnnonceMarketplace.statut == statut
    )
    if categorie is not None:
        requete = requete.filter(AnnonceMarketplace.categorie == categorie)
    if etat is not None:
        requete = requete.filter(AnnonceMarketplace.etat == etat)
    if prix_min is not None:
        requete = requete.filter(AnnonceMarketplace.prix >= prix_min)
    if prix_max is not None:
        requete = requete.filter(AnnonceMarketplace.prix <= prix_max)

    total = requete.with_entities(func.count(AnnonceMarketplace.id)).scalar() or 0
    items = (
        requete.order_by(AnnonceMarketplace.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AnnoncesMarketplacePage(items=items, total=total, page=page, page_size=page_size)


@router.get("/marketplace/annonces/{annonce_id}", response_model=AnnonceMarketplaceDetailOut)
def obtenir_annonce(
    annonce_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> AnnonceMarketplaceDetailOut:
    annonce = db.get(AnnonceMarketplace, annonce_id)
    if annonce is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Annonce introuvable.")
    _verifier_eleve_de_l_etablissement(db, utilisateur, annonce.etablissement_id)
    return _serialiser_annonce_detail(db, annonce, files_client)


@router.delete("/marketplace/annonces/{annonce_id}", status_code=status.HTTP_204_NO_CONTENT)
def retirer_ma_annonce(
    annonce_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> None:
    annonce = db.get(AnnonceMarketplace, annonce_id)
    if annonce is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Annonce introuvable.")
    if annonce.vendeur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette annonce ne vous appartient pas.")
    if annonce.statut != StatutAnnonce.DISPONIBLE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette annonce ne peut plus etre retiree.")

    annonce.statut = StatutAnnonce.RETIREE
    db.commit()


@router.post("/marketplace/annonces/{annonce_id}/retirer", response_model=AnnonceMarketplaceOut)
def retirer_annonce_moderation(
    annonce_id: str,
    payload: RetirerAnnonceRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> AnnonceMarketplace:
    annonce = db.get(AnnonceMarketplace, annonce_id)
    if annonce is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Annonce introuvable.")
    verifier_admin_de_l_etablissement(db, admin, annonce.etablissement_id)
    if annonce.statut == StatutAnnonce.VENDUE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Une annonce deja vendue ne peut pas etre retiree.")
    if annonce.statut == StatutAnnonce.RETIREE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette annonce est deja retiree.")

    if annonce.statut == StatutAnnonce.RESERVEE:
        transaction = _transaction_en_cours(db, annonce.id)
        if transaction is not None:
            transaction.statut = (
                StatutTransactionMarketplace.REMBOURSEE
                if transaction.paiement_confirme
                else StatutTransactionMarketplace.ANNULEE
            )

    annonce.statut = StatutAnnonce.RETIREE
    db.commit()
    db.refresh(annonce)
    return annonce


@router.post(
    "/marketplace/annonces/{annonce_id}/signaler",
    response_model=SignalementAnnonceOut,
    status_code=status.HTTP_201_CREATED,
)
def signaler_annonce(
    annonce_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> SignalementAnnonceMarketplace:
    annonce = db.get(AnnonceMarketplace, annonce_id)
    if annonce is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Annonce introuvable.")
    _verifier_eleve_de_l_etablissement(db, utilisateur, annonce.etablissement_id)

    signalement = SignalementAnnonceMarketplace(annonce_id=annonce_id, signale_par_id=utilisateur.id)
    db.add(signalement)
    db.commit()
    db.refresh(signalement)
    return signalement


@router.get(
    "/etablissements/{etablissement_id}/marketplace/signalements", response_model=list[SignalementAnnonceOut]
)
def signalements_en_attente(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> list[SignalementAnnonceMarketplace]:
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)
    annonce_ids = [
        a.id for a in db.query(AnnonceMarketplace).filter(AnnonceMarketplace.etablissement_id == etablissement_id).all()
    ]
    if not annonce_ids:
        return []
    return (
        db.query(SignalementAnnonceMarketplace)
        .filter(
            SignalementAnnonceMarketplace.annonce_id.in_(annonce_ids),
            SignalementAnnonceMarketplace.traite.is_(False),
        )
        .all()
    )


@router.post("/marketplace/signalements/{signalement_id}/traiter", response_model=SignalementAnnonceOut)
def traiter_signalement_annonce(
    signalement_id: str,
    payload: TraiterSignalementAnnonceRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> SignalementAnnonceMarketplace:
    signalement = db.get(SignalementAnnonceMarketplace, signalement_id)
    if signalement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Signalement introuvable.")
    annonce = db.get(AnnonceMarketplace, signalement.annonce_id)
    verifier_admin_de_l_etablissement(db, admin, annonce.etablissement_id)

    signalement.traite = True
    signalement.decision = payload.decision
    signalement.traite_par_id = admin.id
    db.commit()
    db.refresh(signalement)
    return signalement


@router.get("/mes-annonces-marketplace", response_model=list[AnnonceMarketplaceOut])
def mes_annonces(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> list[AnnonceMarketplace]:
    return (
        db.query(AnnonceMarketplace)
        .filter(AnnonceMarketplace.vendeur_id == utilisateur.id)
        .order_by(AnnonceMarketplace.created_at.desc())
        .all()
    )


@router.post(
    "/marketplace/annonces/{annonce_id}/reserver",
    response_model=TransactionMarketplaceOut,
    status_code=status.HTTP_201_CREATED,
)
def reserver_annonce(
    annonce_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> TransactionMarketplace:
    annonce = db.get(AnnonceMarketplace, annonce_id)
    if annonce is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Annonce introuvable.")
    _verifier_eleve_de_l_etablissement(db, utilisateur, annonce.etablissement_id)
    if annonce.vendeur_id == utilisateur.id:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Vous ne pouvez pas acheter votre propre annonce.")
    if annonce.statut != StatutAnnonce.DISPONIBLE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette annonce n'est pas disponible.")

    transaction = TransactionMarketplace(annonce_id=annonce_id, acheteur_id=utilisateur.id, prix_paye=annonce.prix)
    annonce.statut = StatutAnnonce.RESERVEE
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/marketplace/transactions/{transaction_id}/paiement/amorcer", response_model=TransactionMarketplaceOut)
def amorcer_paiement_transaction(
    transaction_id: str,
    payload: AmorcerPaiementRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> TransactionMarketplace:
    transaction = db.get(TransactionMarketplace, transaction_id)
    if transaction is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Transaction introuvable.")
    if transaction.acheteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette transaction ne vous appartient pas.")
    if transaction.statut != StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette transaction n'attend pas de paiement.")

    transaction.kkiapay_transaction_id = payload.transaction_id
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/marketplace/transactions/{transaction_id}/annuler", response_model=TransactionMarketplaceOut)
def annuler_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> TransactionMarketplace:
    """Annulation reservee a une transaction pas encore payee - complete la panoplie
    de gestes possibles avant paiement confirme, meme logique qu'UC-18 (offre annulable
    tant qu'EN_ATTENTE_PAIEMENT)."""
    transaction = db.get(TransactionMarketplace, transaction_id)
    if transaction is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Transaction introuvable.")
    if transaction.acheteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette transaction ne vous appartient pas.")
    if transaction.statut != StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette transaction ne peut plus etre annulee.")

    transaction.statut = StatutTransactionMarketplace.ANNULEE
    annonce = db.get(AnnonceMarketplace, transaction.annonce_id)
    annonce.statut = StatutAnnonce.DISPONIBLE
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/marketplace/transactions/{transaction_id}/declarer-remise", response_model=TransactionMarketplaceOut)
def declarer_remise(
    transaction_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> TransactionMarketplace:
    transaction = db.get(TransactionMarketplace, transaction_id)
    if transaction is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Transaction introuvable.")
    annonce = db.get(AnnonceMarketplace, transaction.annonce_id)
    if annonce.vendeur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette transaction ne vous appartient pas.")
    if transaction.statut != StatutTransactionMarketplace.PAIEMENT_CONFIRME:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Le paiement n'est pas encore confirme.")

    transaction.statut = StatutTransactionMarketplace.REMISE_DECLAREE
    transaction.date_remise_declaree = datetime.now(timezone.utc)
    transaction.date_limite_confirmation = transaction.date_remise_declaree + _DELAI_CONFIRMATION_RECEPTION
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/marketplace/transactions/{transaction_id}/confirmer", response_model=TransactionMarketplaceOut)
def confirmer_reception(
    transaction_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> TransactionMarketplace:
    transaction = db.get(TransactionMarketplace, transaction_id)
    if transaction is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Transaction introuvable.")
    if transaction.acheteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette transaction ne vous appartient pas.")
    transaction = _appliquer_confirmation_tacite(db, transaction)
    if transaction.statut != StatutTransactionMarketplace.REMISE_DECLAREE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette transaction ne peut pas etre confirmee.")

    transaction.statut = StatutTransactionMarketplace.CONFIRMEE
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post(
    "/marketplace/transactions/{transaction_id}/contester",
    response_model=ContestationMarketplaceOut,
    status_code=status.HTTP_201_CREATED,
)
def contester_transaction(
    transaction_id: str,
    payload: ContesterTransactionRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> ContestationMarketplace:
    transaction = db.get(TransactionMarketplace, transaction_id)
    if transaction is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Transaction introuvable.")
    if transaction.acheteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette transaction ne vous appartient pas.")
    transaction = _appliquer_confirmation_tacite(db, transaction)
    if transaction.statut != StatutTransactionMarketplace.REMISE_DECLAREE:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "statut_invalide",
            "Cette transaction ne peut plus etre contestee (delai depasse ou statut invalide).",
        )

    transaction.statut = StatutTransactionMarketplace.CONTESTEE
    contestation = ContestationMarketplace(transaction_id=transaction_id, motif=payload.motif)
    db.add(contestation)
    db.commit()
    db.refresh(contestation)
    return contestation


@router.post("/marketplace/contestations/{contestation_id}/decision", response_model=ContestationMarketplaceOut)
def decider_contestation(
    contestation_id: str,
    payload: DecisionContestationMarketplaceRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> ContestationMarketplace:
    contestation = db.get(ContestationMarketplace, contestation_id)
    if contestation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contestation introuvable.")
    transaction = db.get(TransactionMarketplace, contestation.transaction_id)
    annonce = db.get(AnnonceMarketplace, transaction.annonce_id)
    verifier_admin_de_l_etablissement(db, admin, annonce.etablissement_id)
    if contestation.statut != StatutContestationMarketplace.EN_ATTENTE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette contestation a deja ete tranchee.")
    if payload.decision == StatutContestationMarketplace.REJETEE and not payload.decision_motif:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "motif_requis", "Un motif est requis en cas de rejet.")
    if payload.decision not in (StatutContestationMarketplace.ACCEPTEE, StatutContestationMarketplace.REJETEE):
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "decision_invalide", "Decision invalide.")

    contestation.statut = payload.decision
    contestation.decision_motif = payload.decision_motif
    contestation.decision_par_id = admin.id
    if payload.decision == StatutContestationMarketplace.ACCEPTEE:
        transaction.statut = StatutTransactionMarketplace.REMBOURSEE
        annonce.statut = StatutAnnonce.DISPONIBLE
    else:
        transaction.statut = StatutTransactionMarketplace.CONFIRMEE
    db.commit()
    db.refresh(contestation)
    return contestation


@router.post("/marketplace/transactions/{transaction_id}/reverser-vendeur", response_model=TransactionMarketplaceOut)
def reverser_vendeur(
    transaction_id: str,
    payload: ReverserVendeurRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> TransactionMarketplace:
    transaction = db.get(TransactionMarketplace, transaction_id)
    if transaction is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Transaction introuvable.")
    annonce = db.get(AnnonceMarketplace, transaction.annonce_id)
    verifier_admin_de_l_etablissement(db, admin, annonce.etablissement_id)
    if transaction.statut != StatutTransactionMarketplace.CONFIRMEE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette transaction n'est pas prete a etre reversee.")

    transaction.reference_paiement_vendeur = payload.reference_paiement
    transaction.statut = StatutTransactionMarketplace.FINALISEE
    annonce.statut = StatutAnnonce.VENDUE
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/mes-transactions-marketplace", response_model=list[TransactionMarketplaceOut])
def mes_transactions(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> list[TransactionMarketplace]:
    mes_annonce_ids = [
        a.id for a in db.query(AnnonceMarketplace).filter(AnnonceMarketplace.vendeur_id == utilisateur.id).all()
    ]
    query = db.query(TransactionMarketplace).filter(
        or_(
            TransactionMarketplace.acheteur_id == utilisateur.id,
            TransactionMarketplace.annonce_id.in_(mes_annonce_ids or [""]),
        )
    )
    return query.order_by(TransactionMarketplace.created_at.desc()).all()
