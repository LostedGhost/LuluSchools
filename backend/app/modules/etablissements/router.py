from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, get_current_user, require_roles
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.core.security import generate_temporary_password, hash_password
from app.modules.etablissements.models import (
    AdminEtablissement,
    Classe,
    Etablissement,
    EtablissementPhoto,
    TypeEtablissement,
)
from app.modules.etablissements.schemas import (
    AnnuairePubliqueOut,
    ClasseCreate,
    ClasseOut,
    EtablissementCreate,
    EtablissementOut,
    EtablissementPhotoOut,
    EtablissementPhotoPubliqueOut,
    EtablissementVitrineOut,
    PosteVitrineOut,
    VitrinePubliqueOut,
    VitrineTotauxOut,
)
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.messagerie.models import Conversation, TypeConversation
from app.modules.recrutement.models import Poste, StatutPoste

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


def _compter_par_etablissement(items: list) -> dict[str, int]:
    compteur: dict[str, int] = {}
    for item in items:
        compteur[item.etablissement_id] = compteur.get(item.etablissement_id, 0) + 1
    return compteur


@router.get("/vitrine-publique", response_model=VitrinePubliqueOut)
def vitrine_publique(db: Session = Depends(get_db)) -> VitrinePubliqueOut:
    """Endpoint public assume (aucune authentification) : teaser leger pour la landing page
    (3 etablissements en avant, quelques postes ouverts, totaux globaux). La plateforme a
    vocation nationale : la liste complete vit dans l'annuaire dedie (GET .../annuaire-public),
    jamais sur la premiere page. Ne renvoie que des champs non sensibles."""
    total_etablissements = db.query(func.count(Etablissement.id)).scalar() or 0
    total_classes = db.query(func.count(Classe.id)).scalar() or 0
    postes_ouverts_tous = db.query(Poste).filter(Poste.statut == StatutPoste.OUVERT).all()

    # En avant : les etablissements qui ont le plus d'opportunites ouvertes en ce moment.
    nb_postes_par_etab = _compter_par_etablissement(postes_ouverts_tous)
    etablissements_en_avant = (
        db.query(Etablissement)
        .order_by(Etablissement.created_at.desc())
        .limit(24)
        .all()
    )
    etablissements_en_avant.sort(key=lambda e: nb_postes_par_etab.get(e.id, 0), reverse=True)
    etablissements_en_avant = etablissements_en_avant[:3]

    classes_par_etab = _compter_par_etablissement(db.query(Classe).all())

    etablissements_out = [
        EtablissementVitrineOut(
            id=e.id,
            nom=e.nom,
            type=e.type,
            statut=e.statut,
            nb_classes=classes_par_etab.get(e.id, 0),
            nb_postes_ouverts=nb_postes_par_etab.get(e.id, 0),
        )
        for e in etablissements_en_avant
    ]

    etab_by_id = {e.id: e for e in etablissements_en_avant}
    postes_out = [
        PosteVitrineOut(
            id=p.id,
            titre=p.titre,
            etablissement_id=p.etablissement_id,
            etablissement_nom=etab_by_id[p.etablissement_id].nom,
            etablissement_type=etab_by_id[p.etablissement_id].type,
        )
        for p in sorted(postes_ouverts_tous, key=lambda p: p.created_at, reverse=True)[:3]
        if p.etablissement_id in etab_by_id
    ]

    return VitrinePubliqueOut(
        etablissements=etablissements_out,
        postes_ouverts=postes_out,
        totaux=VitrineTotauxOut(
            etablissements=total_etablissements,
            classes=total_classes,
            postes_ouverts=len(postes_ouverts_tous),
        ),
    )


@router.get("/annuaire-public", response_model=AnnuairePubliqueOut)
def annuaire_public(
    type: TypeEtablissement | None = None,
    q: str | None = None,
    limit: int = 24,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> AnnuairePubliqueOut:
    """Endpoint public assume (aucune authentification) : annuaire complet et paginable des
    etablissements, sur sa propre page dediee (jamais la landing page — voir vitrine_publique).
    `limit` est plafonne cote serveur quel que soit ce qui est demande, pour ne jamais laisser
    un client construire une reponse geante si le nombre d'etablissements grandit."""
    limit = max(1, min(limit, 60))
    offset = max(0, offset)

    requete = db.query(Etablissement)
    if type is not None:
        requete = requete.filter(Etablissement.type == type)
    if q:
        requete = requete.filter(Etablissement.nom.ilike(f"%{q}%"))

    total = requete.with_entities(func.count(Etablissement.id)).scalar() or 0
    page = requete.order_by(Etablissement.nom.asc()).offset(offset).limit(limit).all()

    ids_page = [e.id for e in page]
    classes_page = db.query(Classe).filter(Classe.etablissement_id.in_(ids_page)).all() if ids_page else []
    postes_page = (
        db.query(Poste)
        .filter(Poste.etablissement_id.in_(ids_page), Poste.statut == StatutPoste.OUVERT)
        .all()
        if ids_page
        else []
    )
    classes_par_etab = _compter_par_etablissement(classes_page)
    postes_par_etab = _compter_par_etablissement(postes_page)

    items = [
        EtablissementVitrineOut(
            id=e.id,
            nom=e.nom,
            type=e.type,
            statut=e.statut,
            nb_classes=classes_par_etab.get(e.id, 0),
            nb_postes_ouverts=postes_par_etab.get(e.id, 0),
        )
        for e in page
    ]

    return AnnuairePubliqueOut(items=items, total=total, limit=limit, offset=offset)


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

    # UC-13 : le groupe de classe de messagerie est cree automatiquement, sa composition
    # est calculee dynamiquement (voir app/modules/messagerie/models.py) - rien d'autre
    # a synchroniser ici.
    db.add(Conversation(type=TypeConversation.GROUPE_CLASSE, classe_id=classe.id))
    db.commit()

    return classe


@router.post(
    "/{etablissement_id}/photos", response_model=EtablissementPhotoOut, status_code=status.HTTP_201_CREATED
)
async def ajouter_photo_etablissement(
    etablissement_id: str,
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
    files_client: LuluFilesClient = Depends(get_files_client),
) -> EtablissementPhoto:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)

    nb_photos = (
        db.query(func.count(EtablissementPhoto.id))
        .filter(EtablissementPhoto.etablissement_id == etablissement_id)
        .scalar()
        or 0
    )
    if nb_photos >= 8:
        raise api_error(status.HTTP_400_BAD_REQUEST, "limite_atteinte", "Maximum 8 photos par etablissement.")

    contenu = await fichier.read()
    try:
        file_id = files_client.upload(
            contenu, fichier.filename or "photo.jpg", fichier.content_type or "image/jpeg"
        )
    except FileStorageError as exc:
        raise api_error(status.HTTP_502_BAD_GATEWAY, "upload_echoue", "Impossible d'envoyer la photo.") from exc

    photo = EtablissementPhoto(etablissement_id=etablissement_id, lulufiles_file_id=file_id, ordre=nb_photos)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.delete("/{etablissement_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_photo_etablissement(
    etablissement_id: str,
    photo_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> None:
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)
    photo = db.get(EtablissementPhoto, photo_id)
    if photo is None or photo.etablissement_id != etablissement_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Photo introuvable.")
    db.delete(photo)
    db.commit()


@router.get("/{etablissement_id}/photos-publiques", response_model=list[EtablissementPhotoPubliqueOut])
def photos_publiques_etablissement(
    etablissement_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
) -> list[EtablissementPhotoPubliqueOut]:
    """Endpoint public assume (aucune authentification) : resout les liens signes a la demande,
    appele uniquement quand un visiteur ouvre une fiche etablissement precise (jamais en masse
    sur la liste/annuaire, pour ne pas multiplier les appels reseau vers LuluFiles)."""
    photos = (
        db.query(EtablissementPhoto)
        .filter(EtablissementPhoto.etablissement_id == etablissement_id)
        .order_by(EtablissementPhoto.ordre.asc())
        .all()
    )
    resultat: list[EtablissementPhotoPubliqueOut] = []
    for photo in photos:
        try:
            url = files_client.get_signed_link(photo.lulufiles_file_id, disposition="inline")
        except FileStorageError:
            continue
        resultat.append(EtablissementPhotoPubliqueOut(id=photo.id, url=url, ordre=photo.ordre))
    return resultat


@router.get("/{etablissement_id}/classes", response_model=list[ClasseOut])
def lister_classes(
    etablissement_id: str,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(get_current_user),
) -> list[Classe]:
    return db.query(Classe).filter(Classe.etablissement_id == etablissement_id).all()
