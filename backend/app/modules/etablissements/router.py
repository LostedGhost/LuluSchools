from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import journaliser_action_ministerielle
from app.core.database import get_db
from app.core.etudiant import est_etudiant as est_etudiant_fn
from app.core.deps import (
    api_error,
    get_current_active_user,
    get_current_user,
    require_roles,
    verifier_portee_etablissement,
)
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.core.security import generate_temporary_password, hash_password
from app.modules.etablissements.models import (
    AdminEtablissement,
    AffectationEnseignant,
    Classe,
    Etablissement,
    EtablissementPhoto,
    RentreeScolaire,
    StatutRentree,
    TypeEtablissement,
    annee_academique_courante,
)
from app.modules.etablissements.schemas import (
    ActionGroupeeEtablissementRequest,
    AffectationEnseignantCreate,
    AffectationEnseignantOut,
    AnnuairePubliqueOut,
    BulletinVieScolaireOut,
    ClasseCreate,
    ClasseOut,
    ConsoleCoursOut,
    ConsoleCoursPageOut,
    ConsoleEleveOut,
    ConsoleElevesPageOut,
    ConsoleEnseignantOut,
    ConsoleEnseignantsPageOut,
    ConsoleNoteOut,
    ConsoleNotesPageOut,
    ConsoleTuteurOut,
    ConsoleTuteursPageOut,
    DescriptionUpdate,
    EleveClasseOut,
    EtablissementCreate,
    EtablissementOut,
    EtablissementPhotoOut,
    EtablissementPhotoPubliqueOut,
    EtablissementVitrineOut,
    InscriptionVieScolaireOut,
    InviterTuteursResponse,
    LocalisationUpdate,
    PosteVitrineOut,
    ProfesseurPrincipalCreate,
    ReconduireClassesRequest,
    RentreeCreate,
    RentreeOut,
    SalleEnseignantOut,
    VieScolaireOut,
    VitrinePubliqueOut,
    VitrineTotauxOut,
)
from app.modules.evaluations.models import Bulletin
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.messagerie.models import Conversation, TypeConversation
from app.modules.pedagogie.models import Cours
from app.modules.recrutement.models import Contrat, Poste, StatutContrat, StatutPoste

router = APIRouter(prefix="/etablissements", tags=["etablissements"])
classes_router = APIRouter(tags=["etablissements"])


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
        latitude=payload.latitude,
        longitude=payload.longitude,
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
    total_etablissements = db.query(func.count(Etablissement.id)).filter(Etablissement.actif.is_(True)).scalar() or 0
    total_classes = db.query(func.count(Classe.id)).scalar() or 0
    postes_ouverts_tous = db.query(Poste).filter(Poste.statut == StatutPoste.OUVERT).all()

    # En avant : les etablissements qui ont le plus d'opportunites ouvertes en ce moment.
    # Un etablissement suspendu (UC-26/42) n'apparait plus sur les vitrines publiques.
    nb_postes_par_etab = _compter_par_etablissement(postes_ouverts_tous)
    etablissements_en_avant = (
        db.query(Etablissement)
        .filter(Etablissement.actif.is_(True))
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
            latitude=e.latitude,
            longitude=e.longitude,
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

    # Un etablissement suspendu (UC-26/42) n'apparait plus dans l'annuaire public.
    requete = db.query(Etablissement).filter(Etablissement.actif.is_(True))
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
            latitude=e.latitude,
            longitude=e.longitude,
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


@router.post("/{etablissement_id}/localisation", response_model=EtablissementOut)
def mettre_a_jour_localisation(
    etablissement_id: str,
    payload: LocalisationUpdate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    ),
) -> Etablissement:
    """Corrige/renseigne les coordonnees d'un etablissement apres coup - l'A++ peut le
    faire pour n'importe quel etablissement (comme le reste de son cycle de vie), l'A+
    seulement pour le sien (le plus souvent en etant physiquement sur place, via la
    geolocalisation du navigateur cote frontend - saisie manuelle en secours)."""
    etablissement = db.get(Etablissement, etablissement_id)
    if etablissement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)

    etablissement.latitude = payload.latitude
    etablissement.longitude = payload.longitude
    db.commit()
    db.refresh(etablissement)
    return etablissement


def _verifier_admin_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    verifier_portee_etablissement(db, utilisateur, etablissement_id)


@router.patch("/{etablissement_id}/description", response_model=EtablissementOut)
def modifier_description_etablissement(
    etablissement_id: str,
    payload: DescriptionUpdate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    ),
) -> Etablissement:
    """UC-23/40 : texte libre affiche sur la fiche etablissement du portail ministeriel
    (comme les photos, l'A++ peut le faire pour n'importe quel etablissement, pas
    seulement l'A+ proprietaire - modération nationale deleguee, cahier des charges)."""
    etablissement = db.get(Etablissement, etablissement_id)
    if etablissement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)

    etablissement.description = payload.description
    db.commit()
    db.refresh(etablissement)
    return etablissement


@router.post("/action-groupee", response_model=list[EtablissementOut])
def appliquer_action_groupee_etablissements(
    payload: ActionGroupeeEtablissementRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[Etablissement]:
    """UC-26/42 : suspendre/reactiver l'homologation de plusieurs etablissements en un
    seul geste. Reserve A++ (contrairement a la description/aux photos, ce pouvoir n'est
    pas delegue a l'A+ - il s'agit d'une decision d'homologation nationale, pas d'une
    mise a jour de fiche). Un etablissement suspendu disparait de l'annuaire/vitrine
    publics (voir annuaire_public/vitrine_publique) mais reste visible et gerable ici."""
    etablissements = db.query(Etablissement).filter(Etablissement.id.in_(payload.ids)).all()
    trouves = {e.id for e in etablissements}
    manquants = set(payload.ids) - trouves
    if manquants:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "introuvable", f"Etablissement(s) introuvable(s) : {', '.join(sorted(manquants))}."
        )

    nouvel_actif = payload.action == "reactiver"
    for etablissement in etablissements:
        etablissement.actif = nouvel_actif
        journaliser_action_ministerielle(
            db, admin, f"etablissement.{payload.action}", "etablissement", etablissement.id, payload.motif
        )
    db.commit()
    for etablissement in etablissements:
        db.refresh(etablissement)
    return etablissements


def _resoudre_annee_academique(db: Session, etablissement_id: str, annee_demandee: str | None) -> str:
    """UC-43/58 : si aucune annee n'est precisee, on reprend celle de la rentree OUVERTE
    de l'etablissement (UC-39/55) si elle existe, sinon un repli calcule sur la date du
    jour - jamais une erreur bloquante, la creation de classe ne doit pas exiger d'avoir
    prealablement declare une rentree."""
    if annee_demandee:
        return annee_demandee
    rentree_ouverte = (
        db.query(RentreeScolaire)
        .filter(RentreeScolaire.etablissement_id == etablissement_id, RentreeScolaire.statut == StatutRentree.OUVERTE)
        .order_by(RentreeScolaire.created_at.desc())
        .first()
    )
    return rentree_ouverte.annee_academique if rentree_ouverte is not None else annee_academique_courante()


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
        filiere=payload.filiere,
        annee_academique=_resoudre_annee_academique(db, etablissement_id, payload.annee_academique),
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
    annee_academique: str | None = None,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(get_current_user),
) -> list[Classe]:
    """UC-45/60 : `annee_academique` optionnel - un client qui veut voir toutes les
    annees (ex. pour peupler un selecteur d'historique) omet le filtre."""
    requete = db.query(Classe).filter(Classe.etablissement_id == etablissement_id)
    if annee_academique:
        requete = requete.filter(Classe.annee_academique == annee_academique)
    return requete.all()


@router.post("/{etablissement_id}/classes/reconduire", response_model=list[ClasseOut])
def reconduire_classes(
    etablissement_id: str,
    payload: ReconduireClassesRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> list[Classe]:
    """UC-44/59 : duplique la STRUCTURE (niveau/filiere/capacite/politique de
    depassement) vers une nouvelle annee academique - jamais les eleves, une reconduction
    demarre toujours vide (l'inscription reste un acte annuel explicite, UC-39/40)."""
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)

    classes = (
        db.query(Classe)
        .filter(Classe.id.in_(payload.classe_ids), Classe.etablissement_id == etablissement_id)
        .all()
    )
    trouvees = {c.id for c in classes}
    manquantes = set(payload.classe_ids) - trouvees
    if manquantes:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "introuvable", f"Classe(s) introuvable(s) : {', '.join(sorted(manquantes))}."
        )

    nouvelles = []
    for classe in classes:
        nouvelle = Classe(
            etablissement_id=etablissement_id,
            niveau=classe.niveau,
            filiere=classe.filiere,
            annee_academique=payload.nouvelle_annee,
            reconduite_depuis_id=classe.id,
            capacite=classe.capacite,
            politique_depassement=classe.politique_depassement,
        )
        db.add(nouvelle)
        nouvelles.append(nouvelle)
    db.commit()

    for nouvelle in nouvelles:
        db.refresh(nouvelle)
        # Meme hook que creer_classe : groupe de messagerie auto-cree pour chaque
        # nouvelle classe.
        db.add(Conversation(type=TypeConversation.GROUPE_CLASSE, classe_id=nouvelle.id))
    db.commit()
    return nouvelles


# ═══════════════════════════════════════════════════════════════
# Rentree scolaire (UC-39/40/55/56)
# ═══════════════════════════════════════════════════════════════


@router.post("/{etablissement_id}/rentrees", response_model=RentreeOut, status_code=status.HTTP_201_CREATED)
def declarer_rentree(
    etablissement_id: str,
    payload: RentreeCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> RentreeScolaire:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)

    # UC-39/55 : une seule rentree OUVERTE a la fois par etablissement - toute rentree
    # deja ouverte est fermee automatiquement (pas d'erreur bloquante, la nouvelle
    # declaration prime).
    db.query(RentreeScolaire).filter(
        RentreeScolaire.etablissement_id == etablissement_id, RentreeScolaire.statut == StatutRentree.OUVERTE
    ).update({"statut": StatutRentree.FERMEE})

    rentree = RentreeScolaire(etablissement_id=etablissement_id, annee_academique=payload.annee_academique)
    db.add(rentree)
    db.commit()
    db.refresh(rentree)
    return rentree


@router.get("/{etablissement_id}/rentrees", response_model=list[RentreeOut])
def lister_rentrees(
    etablissement_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> list[RentreeScolaire]:
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)
    return (
        db.query(RentreeScolaire)
        .filter(RentreeScolaire.etablissement_id == etablissement_id)
        .order_by(RentreeScolaire.created_at.desc())
        .all()
    )


@router.post("/{etablissement_id}/rentrees/{rentree_id}/inviter-tuteurs", response_model=InviterTuteursResponse)
def inviter_tuteurs(
    etablissement_id: str,
    rentree_id: str,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> InviterTuteursResponse:
    """UC-40/56 : notifie les tuteurs des eleves deja connus de cet etablissement (une
    Inscription existe, quel que soit son statut ou son annee) que la rentree est
    ouverte - reutilise BrevoEmailClient, aucun nouveau canal de notification."""
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)
    rentree = db.get(RentreeScolaire, rentree_id)
    if rentree is None or rentree.etablissement_id != etablissement_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Rentree introuvable.")

    classe_ids = db.query(Classe.id).filter(Classe.etablissement_id == etablissement_id)
    eleve_ids = [
        row[0] for row in db.query(Inscription.eleve_id).filter(Inscription.classe_id.in_(classe_ids)).distinct().all()
    ]
    tuteurs = (
        db.query(Utilisateur)
        .join(Eleve, Eleve.tuteur_id == Utilisateur.id)
        .filter(Eleve.id.in_(eleve_ids), Utilisateur.email.isnot(None))
        .distinct()
        .all()
        if eleve_ids
        else []
    )

    etablissement = db.get(Etablissement, etablissement_id)
    nb_notifies = 0
    for tuteur in tuteurs:
        try:
            email_client.send_notification_email(
                to_email=tuteur.email,
                to_name=tuteur.prenom,
                subject=f"Rentree {rentree.annee_academique} ouverte a {etablissement.nom}",
                message=(
                    f"{etablissement.nom} a ouvert les inscriptions pour l'annee academique "
                    f"{rentree.annee_academique}. Connectez-vous a votre espace LuluSchools pour "
                    "(re)inscrire votre enfant."
                ),
            )
        except EmailDeliveryError:
            continue
        nb_notifies += 1
    return InviterTuteursResponse(nb_tuteurs_notifies=nb_notifies)


# ═══════════════════════════════════════════════════════════════
# Vie scolaire (UC-41/42/57)
# ═══════════════════════════════════════════════════════════════


@classes_router.get("/eleves/{eleve_utilisateur_id}/vie-scolaire", response_model=VieScolaireOut)
def consulter_vie_scolaire(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    ),
) -> VieScolaireOut:
    """UC-41/57 : un A+ ne peut lire que si son etablissement a recu AU MOINS UNE
    Inscription de cet eleve (quel que soit son statut ou son annee) - droit de lecture
    permanent une fois acquis, comme un dossier de transfert scolaire reel (voir cahier
    des charges § annexe). L'A++ n'a aucune restriction. Parametre = l'id Utilisateur de
    l'eleve (convention deja utilisee partout ailleurs, ex. eleve_utilisateur_id), jamais
    Eleve.id qui reste un identifiant interne."""
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Eleve introuvable.")

    toutes_inscriptions = (
        db.query(Inscription).filter(Inscription.eleve_id == eleve.id).order_by(Inscription.created_at.desc()).all()
    )
    classe_par_id = {c.id: c for c in db.query(Classe).filter(Classe.id.in_({i.classe_id for i in toutes_inscriptions}))}
    etablissement_ids = {c.etablissement_id for c in classe_par_id.values()}
    etablissements = {e.id: e for e in db.query(Etablissement).filter(Etablissement.id.in_(etablissement_ids)).all()}

    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        lien = db.get(AdminEtablissement, utilisateur.id)
        mon_etablissement_id = lien.etablissement_id if lien is not None else None
        a_recu_une_demande = any(
            classe_par_id[i.classe_id].etablissement_id == mon_etablissement_id for i in toutes_inscriptions
        )
        if not a_recu_une_demande:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "acces_refuse",
                "Votre etablissement n'a jamais recu de demande d'inscription de cet eleve.",
            )

    est_etudiant = est_etudiant_fn(db, eleve.id)
    photo_url = None
    if est_etudiant and eleve.photo_lulufiles_id:
        try:
            photo_url = files_client.get_signed_link(eleve.photo_lulufiles_id, disposition="inline")
        except FileStorageError:
            photo_url = None

    bulletins = db.query(Bulletin).filter(Bulletin.eleve_id == eleve.id).order_by(Bulletin.created_at.desc()).all()
    bulletin_classe_ids = {b.classe_id for b in bulletins} - set(classe_par_id.keys())
    if bulletin_classe_ids:
        classe_par_id.update({c.id: c for c in db.query(Classe).filter(Classe.id.in_(bulletin_classe_ids))})
        nouveaux_etabs = {c.etablissement_id for c in classe_par_id.values()} - set(etablissements.keys())
        if nouveaux_etabs:
            etablissements.update(
                {e.id: e for e in db.query(Etablissement).filter(Etablissement.id.in_(nouveaux_etabs)).all()}
            )

    return VieScolaireOut(
        eleve_id=eleve.id,
        nom=eleve.nom,
        prenom=eleve.prenom,
        date_naissance=eleve.date_naissance,
        matricule=eleve.matricule,
        est_etudiant=est_etudiant,
        photo_url=photo_url,
        inscriptions=[
            InscriptionVieScolaireOut(
                id=i.id,
                etablissement_id=classe_par_id[i.classe_id].etablissement_id,
                etablissement_nom=etablissements[classe_par_id[i.classe_id].etablissement_id].nom,
                classe_niveau=classe_par_id[i.classe_id].niveau,
                classe_filiere=classe_par_id[i.classe_id].filiere,
                annee_academique=classe_par_id[i.classe_id].annee_academique,
                statut=i.statut.value,
                created_at=i.created_at,
            )
            for i in toutes_inscriptions
        ],
        bulletins=[
            BulletinVieScolaireOut(
                id=b.id,
                etablissement_nom=etablissements[classe_par_id[b.classe_id].etablissement_id].nom,
                periode=b.periode,
                moyenne_generale=b.moyenne_generale,
                decision_passage=b.decision_passage,
            )
            for b in bulletins
        ],
    )


# ═══════════════════════════════════════════════════════════════
# Console etablissement (UC-45/46/60/61)
# ═══════════════════════════════════════════════════════════════


def _classes_en_portee(db: Session, etablissement_id: str, classe_id: str | None, annee_academique: str | None) -> list[str]:
    requete = db.query(Classe.id).filter(Classe.etablissement_id == etablissement_id)
    if classe_id:
        requete = requete.filter(Classe.id == classe_id)
    if annee_academique:
        requete = requete.filter(Classe.annee_academique == annee_academique)
    return [row[0] for row in requete.all()]


@router.get("/{etablissement_id}/console/eleves", response_model=ConsoleElevesPageOut)
def console_eleves(
    etablissement_id: str,
    classe_id: str | None = None,
    annee_academique: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> ConsoleElevesPageOut:
    """UC-45/46/60/61 : pivot classe (optionnel) x annee (optionnel, defaut toutes) -
    reutilise DataTable (Phase 5) cote frontend. Pagination serveur obligatoire (meme
    regle qu'ADR-009/Phase 5)."""
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)
    limit = max(1, min(limit, 60))
    offset = max(0, offset)
    classe_ids = _classes_en_portee(db, etablissement_id, classe_id, annee_academique)
    if not classe_ids:
        return ConsoleElevesPageOut(items=[], total=0, limit=limit, offset=offset)

    requete = db.query(Inscription).filter(Inscription.classe_id.in_(classe_ids))
    total = requete.with_entities(func.count(Inscription.id)).scalar() or 0
    page = requete.order_by(Inscription.created_at.desc()).offset(offset).limit(limit).all()

    classes = {c.id: c for c in db.query(Classe).filter(Classe.id.in_({i.classe_id for i in page}))} if page else {}
    eleves = {e.id: e for e in db.query(Eleve).filter(Eleve.id.in_({i.eleve_id for i in page})).all()} if page else {}

    items = [
        ConsoleEleveOut(
            eleve_id=i.eleve_id,
            nom=eleves[i.eleve_id].nom,
            prenom=eleves[i.eleve_id].prenom,
            matricule=eleves[i.eleve_id].matricule,
            classe_id=i.classe_id,
            classe_niveau=classes[i.classe_id].niveau,
            classe_filiere=classes[i.classe_id].filiere,
            statut_inscription=i.statut.value,
        )
        for i in page
    ]
    return ConsoleElevesPageOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/{etablissement_id}/console/enseignants", response_model=ConsoleEnseignantsPageOut)
def console_enseignants(
    etablissement_id: str,
    classe_id: str | None = None,
    annee_academique: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> ConsoleEnseignantsPageOut:
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)
    limit = max(1, min(limit, 60))
    offset = max(0, offset)
    classe_ids = _classes_en_portee(db, etablissement_id, classe_id, annee_academique)
    if not classe_ids:
        return ConsoleEnseignantsPageOut(items=[], total=0, limit=limit, offset=offset)

    requete = db.query(AffectationEnseignant).filter(AffectationEnseignant.classe_id.in_(classe_ids))
    total = requete.with_entities(func.count(AffectationEnseignant.id)).scalar() or 0
    page = requete.order_by(AffectationEnseignant.created_at.desc()).offset(offset).limit(limit).all()

    classes = {c.id: c for c in db.query(Classe).filter(Classe.id.in_({a.classe_id for a in page}))} if page else {}
    enseignants = (
        {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_({a.enseignant_id for a in page})).all()}
        if page
        else {}
    )

    items = [
        ConsoleEnseignantOut(
            utilisateur_id=a.enseignant_id,
            nom=enseignants[a.enseignant_id].nom,
            prenom=enseignants[a.enseignant_id].prenom,
            classe_id=a.classe_id,
            classe_niveau=classes[a.classe_id].niveau,
            classe_filiere=classes[a.classe_id].filiere,
        )
        for a in page
    ]
    return ConsoleEnseignantsPageOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/{etablissement_id}/console/tuteurs", response_model=ConsoleTuteursPageOut)
def console_tuteurs(
    etablissement_id: str,
    classe_id: str | None = None,
    annee_academique: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> ConsoleTuteursPageOut:
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)
    limit = max(1, min(limit, 60))
    offset = max(0, offset)
    classe_ids = _classes_en_portee(db, etablissement_id, classe_id, annee_academique)
    if not classe_ids:
        return ConsoleTuteursPageOut(items=[], total=0, limit=limit, offset=offset)

    eleves_en_portee = (
        db.query(Eleve)
        .join(Inscription, Inscription.eleve_id == Eleve.id)
        .filter(Inscription.classe_id.in_(classe_ids), Eleve.tuteur_id.isnot(None))
        .distinct()
        .all()
    )
    par_tuteur: dict[str, int] = {}
    for eleve in eleves_en_portee:
        par_tuteur[eleve.tuteur_id] = par_tuteur.get(eleve.tuteur_id, 0) + 1

    tuteur_ids = sorted(par_tuteur.keys())
    total = len(tuteur_ids)
    page_ids = tuteur_ids[offset : offset + limit]
    tuteurs = {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_(page_ids)).all()} if page_ids else {}

    items = [
        ConsoleTuteurOut(
            utilisateur_id=tid,
            nom=tuteurs[tid].nom,
            prenom=tuteurs[tid].prenom,
            email=tuteurs[tid].email,
            nb_enfants_dans_le_perimetre=par_tuteur[tid],
        )
        for tid in page_ids
    ]
    return ConsoleTuteursPageOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/{etablissement_id}/console/cours", response_model=ConsoleCoursPageOut)
def console_cours(
    etablissement_id: str,
    classe_id: str | None = None,
    annee_academique: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> ConsoleCoursPageOut:
    """UC-45/46/60/61 : equivalent A+ (scope etablissement) du GET /admin/cours A++
    (Phase 5, scope national)."""
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)
    limit = max(1, min(limit, 60))
    offset = max(0, offset)
    classe_ids = _classes_en_portee(db, etablissement_id, classe_id, annee_academique)
    if not classe_ids:
        return ConsoleCoursPageOut(items=[], total=0, limit=limit, offset=offset)

    requete = db.query(Cours).filter(Cours.classe_id.in_(classe_ids))
    total = requete.with_entities(func.count(Cours.id)).scalar() or 0
    page = requete.order_by(Cours.created_at.desc()).offset(offset).limit(limit).all()

    classes = {c.id: c for c in db.query(Classe).filter(Classe.id.in_({c.classe_id for c in page}))} if page else {}
    enseignants = (
        {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_({c.enseignant_id for c in page})).all()}
        if page
        else {}
    )

    items = [
        ConsoleCoursOut(
            id=cours.id,
            titre=cours.titre,
            chapitre=cours.chapitre,
            classe_id=cours.classe_id,
            classe_niveau=classes[cours.classe_id].niveau,
            enseignant_nom=enseignants[cours.enseignant_id].nom,
            enseignant_prenom=enseignants[cours.enseignant_id].prenom,
        )
        for cours in page
    ]
    return ConsoleCoursPageOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/{etablissement_id}/console/notes", response_model=ConsoleNotesPageOut)
def console_notes(
    etablissement_id: str,
    classe_id: str | None = None,
    annee_academique: str | None = None,
    periode: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> ConsoleNotesPageOut:
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)
    limit = max(1, min(limit, 60))
    offset = max(0, offset)
    classe_ids = _classes_en_portee(db, etablissement_id, classe_id, annee_academique)
    if not classe_ids:
        return ConsoleNotesPageOut(items=[], total=0, limit=limit, offset=offset)

    requete = db.query(Bulletin).filter(Bulletin.classe_id.in_(classe_ids))
    if periode:
        requete = requete.filter(Bulletin.periode == periode)
    total = requete.with_entities(func.count(Bulletin.id)).scalar() or 0
    page = requete.order_by(Bulletin.updated_at.desc()).offset(offset).limit(limit).all()

    classes = {c.id: c for c in db.query(Classe).filter(Classe.id.in_({b.classe_id for b in page}))} if page else {}
    eleves = {e.id: e for e in db.query(Eleve).filter(Eleve.id.in_({b.eleve_id for b in page})).all()} if page else {}

    items = [
        ConsoleNoteOut(
            eleve_id=b.eleve_id,
            eleve_nom=eleves[b.eleve_id].nom,
            eleve_prenom=eleves[b.eleve_id].prenom,
            classe_id=b.classe_id,
            classe_niveau=classes[b.classe_id].niveau,
            periode=b.periode,
            moyenne_generale=b.moyenne_generale,
            decision_passage=b.decision_passage,
        )
        for b in page
    ]
    return ConsoleNotesPageOut(items=items, total=total, limit=limit, offset=offset)


@classes_router.post(
    "/classes/{classe_id}/affectations",
    response_model=AffectationEnseignantOut,
    status_code=status.HTTP_201_CREATED,
)
def affecter_enseignant(
    classe_id: str,
    payload: AffectationEnseignantCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> AffectationEnseignant:
    """Assigne un enseignant a une classe precise : c'est ce lien (et non plus seulement
    le Contrat signe avec l'etablissement) qui determine desormais quelles classes un
    enseignant peut gerer (cours/quiz/devoirs/sessions live) - voir AffectationEnseignant."""
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    verifier_portee_etablissement(db, admin, classe.etablissement_id)

    enseignant = db.get(Utilisateur, payload.enseignant_utilisateur_id)
    if enseignant is None or enseignant.role != RoleUtilisateur.ENSEIGNANT:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Enseignant introuvable.")
    contrat = (
        db.query(Contrat)
        .filter(
            Contrat.enseignant_id == enseignant.id,
            Contrat.etablissement_id == classe.etablissement_id,
            Contrat.statut == StatutContrat.SIGNE,
        )
        .first()
    )
    if contrat is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "contrat_requis",
            "Cet enseignant n'a pas de contrat signe avec cet etablissement.",
        )
    existante = (
        db.query(AffectationEnseignant)
        .filter(AffectationEnseignant.enseignant_id == enseignant.id, AffectationEnseignant.classe_id == classe_id)
        .first()
    )
    if existante is not None:
        raise api_error(status.HTTP_409_CONFLICT, "deja_affecte", "Cet enseignant est deja affecte a cette classe.")

    affectation = AffectationEnseignant(enseignant_id=enseignant.id, classe_id=classe_id)
    db.add(affectation)
    db.commit()
    db.refresh(affectation)
    return affectation


@classes_router.get("/classes/{classe_id}/affectations", response_model=list[AffectationEnseignantOut])
def lister_affectations_classe(
    classe_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[AffectationEnseignant]:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    verifier_portee_etablissement(db, admin, classe.etablissement_id)
    return db.query(AffectationEnseignant).filter(AffectationEnseignant.classe_id == classe_id).all()


@classes_router.delete("/affectations/{affectation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoquer_affectation(
    affectation_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> None:
    affectation = db.get(AffectationEnseignant, affectation_id)
    if affectation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Affectation introuvable.")
    verifier_portee_etablissement(db, admin, affectation.classe.etablissement_id)
    db.delete(affectation)
    db.commit()


def _effectif_classe(db: Session, classe_id: str) -> int:
    return (
        db.query(func.count(Inscription.id))
        .filter(Inscription.classe_id == classe_id, Inscription.statut == StatutInscription.VALIDEE)
        .scalar()
        or 0
    )


@classes_router.get("/mes-classes-affectees", response_model=list[SalleEnseignantOut])
def mes_classes_affectees(
    annee_academique: str | None = None,
    toutes_annees: bool = False,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> list[SalleEnseignantOut]:
    """UC-24 : permet a un enseignant de decouvrir les classes qui lui sont affectees,
    sans devoir deja connaitre leurs id. Par defaut, ne montre que l'annee academique EN
    COURS (une Classe est une instance annuelle, voir annee_academique_courante) ; passer
    toutes_annees=true pour l'historique complet, ou annee_academique='2024-2025' pour une
    annee precise."""
    requete = (
        db.query(AffectationEnseignant, Classe, Etablissement)
        .join(Classe, Classe.id == AffectationEnseignant.classe_id)
        .join(Etablissement, Etablissement.id == Classe.etablissement_id)
        .filter(AffectationEnseignant.enseignant_id == enseignant.id)
    )
    if not toutes_annees:
        requete = requete.filter(Classe.annee_academique == (annee_academique or annee_academique_courante()))

    return [
        SalleEnseignantOut(
            id=classe.id,
            etablissement_id=etablissement.id,
            etablissement_nom=etablissement.nom,
            niveau=classe.niveau,
            capacite=classe.capacite,
            effectif=_effectif_classe(db, classe.id),
            annee_academique=classe.annee_academique,
            est_professeur_principal=affectation.est_professeur_principal,
        )
        for affectation, classe, etablissement in requete.all()
    ]


def _verifier_enseignant_ou_admin_de_la_classe(db: Session, utilisateur: Utilisateur, classe: Classe) -> None:
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        affectation = (
            db.query(AffectationEnseignant)
            .filter(AffectationEnseignant.enseignant_id == utilisateur.id, AffectationEnseignant.classe_id == classe.id)
            .first()
        )
        if affectation is None:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette classe ne vous est pas affectee.")
        return
    verifier_portee_etablissement(db, utilisateur, classe.etablissement_id)


@classes_router.get("/classes/{classe_id}/eleves", response_model=list[EleveClasseOut])
def lister_eleves_de_la_classe(
    classe_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    ),
) -> list[EleveClasseOut]:
    """UC-24.3 : un enseignant affecte a la classe (ou un A+/A++ dans sa portee) voit
    l'effectif nominatif - base de la vue detaillee de salle demandee (etablissement, nom,
    effectif, eleves)."""
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    _verifier_enseignant_ou_admin_de_la_classe(db, utilisateur, classe)

    eleves = (
        db.query(Eleve)
        .join(Inscription, Inscription.eleve_id == Eleve.id)
        .filter(Inscription.classe_id == classe_id, Inscription.statut == StatutInscription.VALIDEE)
        .all()
    )
    return [
        EleveClasseOut(eleve_id=e.id, utilisateur_id=e.utilisateur_id, nom=e.nom, prenom=e.prenom, matricule=e.matricule)
        for e in eleves
    ]


@classes_router.post("/classes/{classe_id}/professeur-principal", response_model=AffectationEnseignantOut)
def designer_professeur_principal(
    classe_id: str,
    payload: ProfesseurPrincipalCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> AffectationEnseignant:
    """UC-23/UC-24 : au plus un professeur principal par classe - voit la vie scolaire
    complete (toutes matieres), contrairement a un enseignant de matiere qui ne voit que
    ses propres entrees (voir vie_scolaire)."""
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    verifier_portee_etablissement(db, admin, classe.etablissement_id)

    cible = (
        db.query(AffectationEnseignant)
        .filter(
            AffectationEnseignant.classe_id == classe_id,
            AffectationEnseignant.enseignant_id == payload.enseignant_utilisateur_id,
        )
        .first()
    )
    if cible is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "affectation_requise",
            "Cet enseignant doit deja etre affecte a cette classe avant de pouvoir en etre professeur principal.",
        )

    autres = (
        db.query(AffectationEnseignant)
        .filter(AffectationEnseignant.classe_id == classe_id, AffectationEnseignant.id != cible.id)
        .all()
    )
    for autre in autres:
        autre.est_professeur_principal = False
    cible.est_professeur_principal = True
    db.commit()
    db.refresh(cible)
    return cible
