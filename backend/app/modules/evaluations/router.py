from dataclasses import dataclass
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, sessionmaker

from app.core.audit import journaliser_action_ministerielle
from app.core.conversion import convertir_en_image
from app.core.database import get_db, get_session_factory
from app.core.deps import api_error, get_current_user, require_roles
from app.core.files import TYPES_DOCUMENT, FileStorageError, LuluFilesClient, get_files_client, lire_upload_borne
from app.core.llm import CorrectionError, FreeLLMClient, get_llm_client
from app.modules.etablissements.models import AdminEtablissement, Classe, Etablissement
from app.modules.actes.generation import CERTIFICAT_REUSSITE, livrer_en_arriere_plan
from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.evaluations import periodes as periodes_evaluation
from app.modules.evaluations.decisions import est_favorable
from app.modules.evaluations.bulletin_pdf import generer_pdf_bulletin
from app.modules.evaluations.models import (
    Bulletin,
    Devoir,
    NatureEvaluation,
    QuestionDevoir,
    ReferentielCoefficient,
    ReponseSoumission,
    Soumission,
    StatutReferentiel,
    StatutSoumission,
)
from app.modules.evaluations.schemas import (
    AdminDevoirOut,
    AdminDevoirPageOut,
    BulletinOut,
    CorrectionNoteGlobaleRequest,
    CorrectionRequest,
    DevoirCreate,
    DevoirOut,
    DevoirProprietaireOut,
    LienFichierOut,
    MasquerContenuRequest,
    QuestionDevoirAvecBaremeOut,
    ReferentielCreate,
    ReferentielOut,
    ReferentielPropositionCreate,
    ReferentielUpdate,
    SoumissionCreate,
    SoumissionOut,
    ValiderLotRequest,
    ValiderPassageRequest,
)
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.pedagogie.router import _verifier_eleve_inscrit, _verifier_enseignant_rattache

MAX_TAILLE_DOCUMENT_EVALUATION_OCTETS = 20 * 1024 * 1024

router = APIRouter(tags=["evaluations"])


@router.post("/classes/{classe_id}/devoirs", response_model=DevoirOut, status_code=status.HTTP_201_CREATED)
def creer_devoir(
    classe_id: str,
    payload: DevoirCreate,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Devoir:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    _verifier_enseignant_rattache(db, enseignant, classe.id)

    devoir = Devoir(
        classe_id=classe_id,
        enseignant_id=enseignant.id,
        titre=payload.titre,
        matiere=payload.matiere,
        date_limite=payload.date_limite,
        bareme=payload.bareme,
        nature=payload.nature,
    )
    db.add(devoir)
    db.flush()
    for ordre, question in enumerate(payload.questions):
        db.add(
            QuestionDevoir(
                devoir_id=devoir.id,
                ordre=ordre,
                enonce=question.enonce,
                bareme_reponse=question.bareme_reponse,
                points_max=question.points_max,
            )
        )
    db.commit()
    db.refresh(devoir)
    return devoir


def _refuser_si_masque(devoir: Devoir) -> None:
    """Un devoir masque par le Ministere n'existe plus pour l'eleve et son tuteur (meme
    regle que la liste des devoirs) - y compris par lien direct ou soumission."""
    if devoir.masque_par_id is not None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")


def _verifier_proprietaire_du_devoir(db: Session, enseignant: Utilisateur, devoir: Devoir) -> None:
    if devoir.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")


@router.post("/devoirs/{devoir_id}/sujet-document", response_model=DevoirOut)
def televerser_sujet_document(
    devoir_id: str,
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Devoir:
    """UC-26.2 : sujet libre (image et/ou PDF) en complement du formulaire de questions
    structure - visible par l'eleve (voir obtenir_lien_sujet_document), contrairement au
    document de bareme (voir televerser_bareme_document)."""
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    _verifier_proprietaire_du_devoir(db, enseignant, devoir)

    contenu = lire_upload_borne(fichier, MAX_TAILLE_DOCUMENT_EVALUATION_OCTETS, TYPES_DOCUMENT)
    try:
        devoir.sujet_lulufiles_file_id = files_client.upload(
            contenu, fichier.filename or "sujet", fichier.content_type or "application/octet-stream"
        )
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible de stocker le fichier, veuillez réessayer."
        ) from exc
    db.commit()
    db.refresh(devoir)
    return devoir


@router.get("/devoirs/{devoir_id}/sujet-document/lien", response_model=LienFichierOut)
def obtenir_lien_sujet_document(
    devoir_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ELEVE)),
) -> LienFichierOut:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    if utilisateur.role == RoleUtilisateur.ELEVE:
        _verifier_eleve_inscrit(db, utilisateur.id, devoir.classe_id)
        _refuser_si_masque(devoir)
    else:
        _verifier_proprietaire_du_devoir(db, utilisateur, devoir)
    if not devoir.sujet_lulufiles_file_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ce devoir n'a pas de sujet en document.")

    try:
        url = files_client.get_signed_link(devoir.sujet_lulufiles_file_id, disposition="inline")
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible d'obtenir le lien, veuillez réessayer."
        ) from exc
    return LienFichierOut(url=url)


@router.post("/devoirs/{devoir_id}/bareme-document", response_model=DevoirProprietaireOut)
def televerser_bareme_document(
    devoir_id: str,
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Devoir:
    """UC-26.3 : bareme GLOBAL sous forme de document, en complement du bareme par
    question deja existant - jamais expose a l'eleve (voir DevoirProprietaireOut)."""
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    _verifier_proprietaire_du_devoir(db, enseignant, devoir)

    contenu = lire_upload_borne(fichier, MAX_TAILLE_DOCUMENT_EVALUATION_OCTETS, TYPES_DOCUMENT)
    try:
        devoir.bareme_document_lulufiles_file_id = files_client.upload(
            contenu, fichier.filename or "bareme", fichier.content_type or "application/octet-stream"
        )
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible de stocker le fichier, veuillez réessayer."
        ) from exc
    db.commit()
    db.refresh(devoir)
    return devoir


@router.get("/devoirs/{devoir_id}/bareme-document/lien", response_model=LienFichierOut)
def obtenir_lien_bareme_document(
    devoir_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> LienFichierOut:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    _verifier_proprietaire_du_devoir(db, enseignant, devoir)
    if not devoir.bareme_document_lulufiles_file_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ce devoir n'a pas de document de barème.")

    try:
        url = files_client.get_signed_link(devoir.bareme_document_lulufiles_file_id, disposition="inline")
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible d'obtenir le lien, veuillez réessayer."
        ) from exc
    return LienFichierOut(url=url)


def _verifier_tuteur_a_un_enfant_dans_la_classe(db: Session, tuteur_id: str, classe_id: str) -> None:
    """UC-31 : un tuteur suit les devoirs de SON enfant, jamais d'une classe au hasard -
    meme garde-fou que cours_direct._verifier_tuteur_a_un_enfant_dans_la_classe."""
    a_un_enfant = (
        db.query(Inscription)
        .join(Eleve, Eleve.id == Inscription.eleve_id)
        .filter(
            Eleve.tuteur_id == tuteur_id,
            Inscription.classe_id == classe_id,
            Inscription.statut == StatutInscription.VALIDEE,
        )
        .first()
        is not None
    )
    if not a_un_enfant:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Aucun de vos enfants n'est inscrit dans cette classe.")


@router.get("/devoirs/{devoir_id}", response_model=DevoirOut)
def obtenir_devoir(
    devoir_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(
            RoleUtilisateur.ENSEIGNANT,
            RoleUtilisateur.ELEVE,
            RoleUtilisateur.TUTEUR,
            RoleUtilisateur.ADMIN_ETABLISSEMENT,
            RoleUtilisateur.ADMIN_MINISTERIEL,
        )
    ),
) -> Devoir:
    """Portee verifiee ici (auparavant absente : n'importe quel role autorise pouvait
    lire n'importe quel devoir d'un autre etablissement/classe en devinant l'id) -
    meme logique que lister_devoirs ci-dessous, par classe/etablissement."""
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    if utilisateur.role == RoleUtilisateur.ADMIN_MINISTERIEL:
        return devoir

    classe = db.get(Classe, devoir.classe_id)
    if utilisateur.role == RoleUtilisateur.ELEVE:
        _verifier_eleve_inscrit(db, utilisateur.id, devoir.classe_id)
        _refuser_si_masque(devoir)
    elif utilisateur.role == RoleUtilisateur.TUTEUR:
        _verifier_tuteur_a_un_enfant_dans_la_classe(db, utilisateur.id, devoir.classe_id)
        _refuser_si_masque(devoir)
    elif utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        _verifier_enseignant_rattache(db, utilisateur, classe.id)
    else:
        lien = db.get(AdminEtablissement, utilisateur.id)
        if lien is None or lien.etablissement_id != classe.etablissement_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet établissement.")
    return devoir


@router.get("/classes/{classe_id}/devoirs", response_model=list[DevoirOut])
def lister_devoirs(
    classe_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(
            RoleUtilisateur.ELEVE,
            RoleUtilisateur.TUTEUR,
            RoleUtilisateur.ENSEIGNANT,
            RoleUtilisateur.ADMIN_ETABLISSEMENT,
            RoleUtilisateur.ADMIN_MINISTERIEL,
        )
    ),
) -> list[Devoir]:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    requete = db.query(Devoir).filter(Devoir.classe_id == classe_id)
    if utilisateur.role == RoleUtilisateur.ELEVE:
        _verifier_eleve_inscrit(db, utilisateur.id, classe_id)
        # UC-37/53 (lot admin ministeriel) : meme regle que lister_cours (pedagogie) - un
        # devoir masque par le Ministere reste visible a l'enseignant/A+/A++, pas a l'eleve.
        requete = requete.filter(Devoir.masque_par_id.is_(None))
    elif utilisateur.role == RoleUtilisateur.TUTEUR:
        _verifier_tuteur_a_un_enfant_dans_la_classe(db, utilisateur.id, classe_id)
        # Meme regle que pour l'eleve : le tuteur voit ce que voit son enfant, pas plus.
        requete = requete.filter(Devoir.masque_par_id.is_(None))
    elif utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        _verifier_enseignant_rattache(db, utilisateur, classe.id)
    elif utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        lien = db.get(AdminEtablissement, utilisateur.id)
        if lien is None or lien.etablissement_id != classe.etablissement_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet établissement.")
    return requete.all()


@router.get("/devoirs/{devoir_id}/ma-soumission", response_model=SoumissionOut)
def obtenir_ma_soumission(
    devoir_id: str,
    db: Session = Depends(get_db),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> Soumission:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur.id).first()
    soumission = (
        db.query(Soumission).filter(Soumission.devoir_id == devoir_id, Soumission.eleve_id == eleve.id).first()
        if eleve is not None
        else None
    )
    if soumission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Aucune soumission pour ce devoir.")
    return soumission


@router.post(
    "/devoirs/{devoir_id}/soumissions", response_model=SoumissionOut, status_code=status.HTTP_201_CREATED
)
def soumettre_devoir(
    devoir_id: str,
    payload: SoumissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    session_factory: sessionmaker = Depends(get_session_factory),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> Soumission:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    eleve = _verifier_eleve_inscrit(db, eleve_utilisateur.id, devoir.classe_id)
    _refuser_si_masque(devoir)

    date_limite = devoir.date_limite if devoir.date_limite.tzinfo else devoir.date_limite.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > date_limite:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "delai_depasse",
            "La date limite est dépassée : la note zéro s'applique automatiquement, sans dérogation.",
        )
    if db.query(Soumission).filter(Soumission.devoir_id == devoir_id, Soumission.eleve_id == eleve.id).first():
        raise api_error(status.HTTP_409_CONFLICT, "deja_soumis", "Vous avez déjà soumis ce devoir.")

    questions_par_id = {q.id: q for q in devoir.questions}
    if {r.question_id for r in payload.reponses} != set(questions_par_id.keys()):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "reponses_incompletes",
            "Une réponse est attendue pour chaque question du devoir, exactement.",
        )

    soumission = Soumission(devoir_id=devoir_id, eleve_id=eleve.id, statut=StatutSoumission.EN_CORRECTION)
    db.add(soumission)
    db.flush()

    for reponse in payload.reponses:
        question = questions_par_id[reponse.question_id]
        db.add(
            ReponseSoumission(
                soumission_id=soumission.id, question_id=question.id, texte_reponse=reponse.texte_reponse
            )
        )

    db.commit()
    db.refresh(soumission)

    background_tasks.add_task(
        _corriger_soumission_en_arriere_plan,
        soumission.id,
        llm_client,
        devoir.bareme.value == "rigide",
        session_factory,
    )
    return soumission


@router.post(
    "/devoirs/{devoir_id}/soumissions/copie-image",
    response_model=SoumissionOut,
    status_code=status.HTTP_201_CREATED,
)
def soumettre_devoir_par_copie_image(
    devoir_id: str,
    background_tasks: BackgroundTasks,
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    files_client: LuluFilesClient = Depends(get_files_client),
    session_factory: sessionmaker = Depends(get_session_factory),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> Soumission:
    """UC-26.4 : alternative au formulaire de reponses texte (POST .../soumissions) - une
    seule photo/scan de la copie complete, corrigee de facon holistique (une note globale,
    pas de decoupage par question - voir FreeLLMClient.corriger_copie_image). Memes regles
    que la soumission texte (delai, unicite) ; les deux voies restent mutuellement
    exclusives pour une meme soumission."""
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    eleve = _verifier_eleve_inscrit(db, eleve_utilisateur.id, devoir.classe_id)
    _refuser_si_masque(devoir)

    date_limite = devoir.date_limite if devoir.date_limite.tzinfo else devoir.date_limite.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > date_limite:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "delai_depasse",
            "La date limite est dépassée : la note zéro s'applique automatiquement, sans dérogation.",
        )
    if db.query(Soumission).filter(Soumission.devoir_id == devoir_id, Soumission.eleve_id == eleve.id).first():
        raise api_error(status.HTTP_409_CONFLICT, "deja_soumis", "Vous avez déjà soumis ce devoir.")

    contenu = lire_upload_borne(fichier, MAX_TAILLE_DOCUMENT_EVALUATION_OCTETS, TYPES_DOCUMENT)
    try:
        copie_lulufiles_file_id = files_client.upload(
            contenu, fichier.filename or "copie", fichier.content_type or "application/octet-stream"
        )
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible de stocker le fichier, veuillez réessayer."
        ) from exc

    # Conversion locale (PyMuPDF, pas de reseau) : reste synchrone - seul l'appel FreeLLM
    # part en arriere-plan (ADR-005), memes principes que recrutement/router.py.
    image_bytes, image_content_type = convertir_en_image(contenu, fichier.content_type or "application/octet-stream")

    soumission = Soumission(
        devoir_id=devoir_id,
        eleve_id=eleve.id,
        statut=StatutSoumission.EN_CORRECTION,
        copie_image_lulufiles_file_id=copie_lulufiles_file_id,
    )
    db.add(soumission)
    db.commit()
    db.refresh(soumission)

    background_tasks.add_task(
        _corriger_copie_image_en_arriere_plan,
        soumission.id,
        llm_client,
        devoir.bareme.value == "rigide",
        session_factory,
        image_bytes,
        image_content_type,
    )
    return soumission


def _corriger_copie_image_en_arriere_plan(
    soumission_id: str,
    llm_client: FreeLLMClient,
    strict: bool,
    session_factory: sessionmaker,
    image_bytes: bytes,
    image_content_type: str,
) -> None:
    db = session_factory()
    try:
        soumission = db.get(Soumission, soumission_id)
        if soumission is None:
            return
        devoir = db.get(Devoir, soumission.devoir_id)
        questions = sorted(devoir.questions, key=lambda q: q.ordre)
        consigne_globale = "\n\n".join(
            f"Question : {q.enonce}\nBareme ({q.points_max} points) : {q.bareme_reponse}" for q in questions
        )
        points_max_total = sum(q.points_max for q in questions) or 1.0

        try:
            soumission.note = llm_client.corriger_copie_image(
                consigne_globale, points_max_total, image_bytes, image_content_type, strict=strict
            )
            soumission.statut = StatutSoumission.CORRIGEE
        except CorrectionError:
            soumission.statut = StatutSoumission.ECHEC_CORRECTION
            soumission.note = None
        db.commit()
    finally:
        db.close()


def _corriger_soumission_en_arriere_plan(
    soumission_id: str, llm_client: FreeLLMClient, strict: bool, session_factory: sessionmaker
) -> None:
    """Execute apres l'envoi de la reponse HTTP (voir BackgroundTasks sur
    soumettre_devoir) : ouvre sa propre session DB via session_factory (celle de la
    requete est deja fermee). llm_client et session_factory sont ceux deja resolus par
    Depends au moment de la requete (donc les fakes injectes par les tests en
    environnement de test), jamais reconstruits ici."""
    db = session_factory()
    try:
        soumission = db.get(Soumission, soumission_id)
        if soumission is None:
            return
        devoir = db.get(Devoir, soumission.devoir_id)
        questions_par_id = {q.id: q for q in devoir.questions}

        echec = False
        for reponse_orm in soumission.reponses:
            question = questions_par_id[reponse_orm.question_id]
            try:
                reponse_orm.points_obtenus = llm_client.corriger_reponse(
                    question.enonce, question.bareme_reponse, question.points_max,
                    reponse_orm.texte_reponse, strict=strict,
                )
            except CorrectionError:
                echec = True

        if echec:
            soumission.statut = StatutSoumission.ECHEC_CORRECTION
            soumission.note = None
        else:
            soumission.statut = StatutSoumission.CORRIGEE
            soumission.note = sum(r.points_obtenus for r in soumission.reponses)
        db.commit()
    finally:
        db.close()


@router.get("/soumissions/{soumission_id}", response_model=SoumissionOut)
def obtenir_soumission(
    soumission_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(
            RoleUtilisateur.ELEVE,
            RoleUtilisateur.TUTEUR,
            RoleUtilisateur.ENSEIGNANT,
            RoleUtilisateur.ADMIN_ETABLISSEMENT,
            RoleUtilisateur.ADMIN_MINISTERIEL,
        )
    ),
) -> Soumission:
    """Permet a l'eleve (et depuis UC-31, a son tuteur) de suivre l'avancement de la
    correction (statut=en_correction tant que le traitement en arriere-plan n'est pas
    termine) - jusqu'ici le tuteur ne voyait que le bulletin final, jamais une
    soumission en cours."""
    soumission = db.get(Soumission, soumission_id)
    if soumission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Soumission introuvable.")
    devoir = db.get(Devoir, soumission.devoir_id)
    eleve_de_la_soumission = db.get(Eleve, soumission.eleve_id)

    if utilisateur.role == RoleUtilisateur.ELEVE:
        if eleve_de_la_soumission is None or eleve_de_la_soumission.utilisateur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette soumission ne vous appartient pas.")
    elif utilisateur.role == RoleUtilisateur.TUTEUR:
        if eleve_de_la_soumission is None or eleve_de_la_soumission.tuteur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette soumission ne concerne pas votre enfant.")
    elif utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        if devoir.enseignant_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")
    elif utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        classe = db.get(Classe, devoir.classe_id)
        lien = db.get(AdminEtablissement, utilisateur.id)
        if lien is None or lien.etablissement_id != classe.etablissement_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet établissement.")

    return soumission


@router.get("/devoirs/{devoir_id}/soumission-de/{eleve_utilisateur_id}", response_model=SoumissionOut)
def obtenir_soumission_de_mon_enfant(
    devoir_id: str,
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> Soumission:
    """UC-31.2 : equivalent de GET /devoirs/{id}/ma-soumission (reserve a ELEVE) pour un
    tuteur qui n'a pas encore l'id de la soumission - lui permet de decouvrir l'etat
    d'un devoir de son enfant sans devoir d'abord passer par obtenir_soumission."""
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None or eleve.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet élève n'est pas rattaché à votre compte.")

    soumission = db.query(Soumission).filter(Soumission.devoir_id == devoir_id, Soumission.eleve_id == eleve.id).first()
    if soumission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Aucune soumission pour ce devoir.")
    return soumission


@router.post("/soumissions/{soumission_id}/corriger", response_model=SoumissionOut)
def corriger_soumission(
    soumission_id: str,
    payload: CorrectionRequest,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Soumission:
    """Ecran de revision manuelle : sert a la fois de filet de secours quand la
    correction automatique a echoue (statut=echec_correction) et de possibilite de
    surcharger une correction LLM deja faite."""
    soumission = db.get(Soumission, soumission_id)
    if soumission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Soumission introuvable.")
    devoir = db.get(Devoir, soumission.devoir_id)
    if devoir.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")

    points_max_par_question = {q.id: q.points_max for q in devoir.questions}
    reponses_par_id = {r.question_id: r for r in soumission.reponses}
    for correction in payload.reponses:
        if correction.question_id not in reponses_par_id:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "question_inconnue", "Question hors de ce devoir.")
        if correction.points_obtenus > points_max_par_question[correction.question_id]:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "points_hors_bareme", "Les points attribués dépassent le maximum de la question."
            )
        reponses_par_id[correction.question_id].points_obtenus = correction.points_obtenus

    soumission.note = sum(r.points_obtenus or 0 for r in soumission.reponses)
    soumission.statut = StatutSoumission.CORRIGEE
    db.commit()
    db.refresh(soumission)
    return soumission


@router.post("/soumissions/{soumission_id}/corriger-note-globale", response_model=SoumissionOut)
def corriger_note_globale(
    soumission_id: str,
    payload: CorrectionNoteGlobaleRequest,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Soumission:
    """Equivalent de corriger_soumission (ci-dessus) pour une soumission par copie image
    (UC-26.4) : pas de decoupage par question a surcharger, une seule note globale."""
    soumission = db.get(Soumission, soumission_id)
    if soumission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Soumission introuvable.")
    devoir = db.get(Devoir, soumission.devoir_id)
    if devoir.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")
    if soumission.copie_image_lulufiles_file_id is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "soumission_non_imagee",
            "Cette copie a été saisie en ligne : corrigez-la question par question.",
        )
    points_max_total = sum(q.points_max for q in devoir.questions) or 1.0
    if payload.note > points_max_total:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "note_hors_bareme", "La note dépasse le total du barème.")

    soumission.note = payload.note
    soumission.statut = StatutSoumission.CORRIGEE
    db.commit()
    db.refresh(soumission)
    return soumission


@router.get("/devoirs/{devoir_id}/questions-bareme", response_model=list[QuestionDevoirAvecBaremeOut])
def lister_questions_avec_bareme(
    devoir_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> list[QuestionDevoir]:
    """Bug reel corrige (audit frontend, 2026-09-25) : l'ecran de revision manuelle
    affichait un champ de points par question sans jamais montrer le bareme que
    l'enseignant avait lui-meme redige pour l'IA - il devait s'en souvenir ou rouvrir le
    devoir ailleurs. Reserve au proprietaire du devoir : voir la note sur
    QuestionDevoirAvecBaremeOut pour pourquoi ce n'est jamais mis sur DevoirOut."""
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    if devoir.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")
    return sorted(devoir.questions, key=lambda q: q.ordre)


@router.get("/devoirs/{devoir_id}/soumissions-a-revoir", response_model=list[SoumissionOut])
def lister_soumissions_a_revoir(
    devoir_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> list[Soumission]:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    if devoir.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")
    return (
        db.query(Soumission)
        .filter(Soumission.devoir_id == devoir_id, Soumission.statut == StatutSoumission.ECHEC_CORRECTION)
        .all()
    )


@router.get("/referentiels-coefficients", response_model=list[ReferentielOut])
def lister_referentiels(
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ADMIN_MINISTERIEL, RoleUtilisateur.ADMIN_ETABLISSEMENT)
    ),
) -> list[ReferentielCoefficient]:
    """Sans cette liste, ni le ministere ni un A+ ne peuvent decouvrir les referentiels
    existants ou les propositions en attente sans deja en connaitre les id (UC-09).
    Un A+ ne doit voir que les referentiels nationaux (etablissement_proposant_id NULL)
    et ses PROPRES propositions, jamais celles d'un etablissement concurrent."""
    requete = db.query(ReferentielCoefficient)
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        lien = db.get(AdminEtablissement, utilisateur.id)
        etablissement_id = lien.etablissement_id if lien is not None else None
        requete = requete.filter(
            or_(
                ReferentielCoefficient.etablissement_proposant_id.is_(None),
                ReferentielCoefficient.etablissement_proposant_id == etablissement_id,
            )
        )
    return requete.order_by(ReferentielCoefficient.created_at.desc()).all()


@router.post(
    "/referentiels-coefficients", response_model=ReferentielOut, status_code=status.HTTP_201_CREATED
)
def creer_referentiel(
    payload: ReferentielCreate,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ReferentielCoefficient:
    referentiel = ReferentielCoefficient(
        niveau=payload.niveau,
        matiere=payload.matiere,
        coefficient=payload.coefficient,
        statut=StatutReferentiel.VALIDE,
    )
    db.add(referentiel)
    db.commit()
    db.refresh(referentiel)
    return referentiel


@router.post(
    "/referentiels-coefficients/{referentiel_id}/proposition",
    response_model=ReferentielOut,
    status_code=status.HTTP_201_CREATED,
)
def proposer_mise_a_jour_referentiel(
    referentiel_id: str,
    payload: ReferentielPropositionCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> ReferentielCoefficient:
    existant = db.get(ReferentielCoefficient, referentiel_id)
    if existant is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Référentiel introuvable.")
    lien = db.get(AdminEtablissement, admin.id)

    proposition = ReferentielCoefficient(
        niveau=existant.niveau,
        matiere=existant.matiere,
        coefficient=payload.coefficient,
        statut=StatutReferentiel.PROPOSITION_EN_ATTENTE,
        etablissement_proposant_id=lien.etablissement_id if lien else None,
        propose_pour_id=existant.id,
    )
    db.add(proposition)
    db.commit()
    db.refresh(proposition)
    return proposition


@router.post("/referentiels-coefficients/{referentiel_id}/valider", response_model=ReferentielOut)
def valider_referentiel(
    referentiel_id: str,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ReferentielCoefficient:
    proposition = db.get(ReferentielCoefficient, referentiel_id)
    if proposition is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Référentiel introuvable.")
    if proposition.statut != StatutReferentiel.PROPOSITION_EN_ATTENTE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce référentiel n'est pas une proposition en attente.")

    proposition.statut = StatutReferentiel.VALIDE
    if proposition.propose_pour_id:
        ancien = db.get(ReferentielCoefficient, proposition.propose_pour_id)
        if ancien is not None:
            ancien.statut = StatutReferentiel.REMPLACE

    db.commit()
    db.refresh(proposition)
    return proposition


@router.patch("/referentiels-coefficients/{referentiel_id}", response_model=ReferentielOut)
def modifier_referentiel(
    referentiel_id: str,
    payload: ReferentielUpdate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ReferentielCoefficient:
    """UC-28/44 : edition directe d'un referentiel VALIDE par l'A++, sans repasser par le
    cycle proposition/validation (reserve a l'A+, voir proposer_mise_a_jour_referentiel) -
    l'A++ est deja l'autorite finale, un aller-retour avec lui-meme n'aurait aucun sens."""
    referentiel = db.get(ReferentielCoefficient, referentiel_id)
    if referentiel is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Référentiel introuvable.")
    if referentiel.statut != StatutReferentiel.VALIDE:
        raise api_error(
            status.HTTP_409_CONFLICT, "statut_invalide", "Seul un référentiel en vigueur peut être modifié directement."
        )

    referentiel.coefficient = payload.coefficient
    journaliser_action_ministerielle(
        db, admin, "referentiel.modifier", "referentiel", referentiel.id, f"nouveau coefficient={payload.coefficient}"
    )
    db.commit()
    db.refresh(referentiel)
    return referentiel


@router.post("/referentiels-coefficients/valider-lot", response_model=list[ReferentielOut])
def valider_referentiels_en_lot(
    payload: ValiderLotRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[ReferentielCoefficient]:
    """UC-29/45 : valider plusieurs propositions en attente en un seul geste plutot qu'une
    a la fois - reutilise exactement la logique de valider_referentiel ci-dessus."""
    propositions = db.query(ReferentielCoefficient).filter(ReferentielCoefficient.id.in_(payload.ids)).all()
    trouves = {p.id for p in propositions}
    manquants = set(payload.ids) - trouves
    if manquants:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "introuvable", f"Référentiel(s) introuvable(s) : {', '.join(sorted(manquants))}."
        )
    non_en_attente = [p.id for p in propositions if p.statut != StatutReferentiel.PROPOSITION_EN_ATTENTE]
    if non_en_attente:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "statut_invalide",
            f"Référentiel(s) pas en attente de validation : {', '.join(sorted(non_en_attente))}.",
        )

    for proposition in propositions:
        proposition.statut = StatutReferentiel.VALIDE
        if proposition.propose_pour_id:
            ancien = db.get(ReferentielCoefficient, proposition.propose_pour_id)
            if ancien is not None:
                ancien.statut = StatutReferentiel.REMPLACE
        journaliser_action_ministerielle(db, admin, "referentiel.valider_lot", "referentiel", proposition.id, None)

    db.commit()
    for proposition in propositions:
        db.refresh(proposition)
    return propositions


def _coefficient_pour(db: Session, niveau: str, matiere: str) -> float:
    referentiel = (
        db.query(ReferentielCoefficient)
        .filter(
            ReferentielCoefficient.niveau == niveau,
            ReferentielCoefficient.matiere == matiere,
            ReferentielCoefficient.statut == StatutReferentiel.VALIDE,
        )
        .first()
    )
    return referentiel.coefficient if referentiel is not None else 1.0


@dataclass(frozen=True)
class NoteDuBulletin:
    """Une evaluation comptee dans le bulletin d'une periode (detail du bulletin PDF)."""

    devoir: Devoir
    note: float | None  # note brute sur `total` ; None = copie non rendue (compte 0)
    total: float
    sur_100: float
    coefficient: float


def notes_de_la_periode(db: Session, eleve: Eleve, classe_id: str, periode: str) -> list[tuple[str, float, float]]:
    """(matiere, note sur 100, coefficient) de chaque devoir comptant dans le bulletin."""
    return [(n.devoir.matiere, n.sur_100, n.coefficient) for n in evaluations_de_la_periode(db, eleve, classe_id, periode)]


def evaluations_de_la_periode(db: Session, eleve: Eleve, classe_id: str, periode: str) -> list[NoteDuBulletin]:
    """Chaque devoir SOMMATIF de la periode qui compte dans le bulletin, par date. Chaque devoir est normalise sur 100 (note / somme des
    points_max de ses questions), pondere par le coefficient (niveau, matiere) du
    referentiel valide en vigueur - defaut 1.0 (UC-09). Un devoir compte des qu'il est
    corrige (meme avant son echeance) ; sans soumission, il compte 0 une fois l'echeance
    passee - avant, il n'y a simplement pas encore de resultat."""
    classe = db.get(Classe, classe_id)
    etablissement = db.get(Etablissement, classe.etablissement_id)
    periode_evaluee = periodes_evaluation.trouver(etablissement.type, classe.annee_academique, periode)
    if periode_evaluee is None:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "periode_invalide", "Cette période n'existe pas pour cette classe.")
    debut, fin = periodes_evaluation.bornes_utc(periode_evaluee)
    # UC-26.1 : une evaluation FORMATIVE ne compte jamais dans la moyenne officielle du
    # bulletin - seules les SOMMATIVES sont incluses, et seulement celles de la periode
    # (date limite comprise dans ses bornes).
    devoirs = (
        db.query(Devoir)
        .filter(
            Devoir.classe_id == classe_id,
            Devoir.nature == NatureEvaluation.SOMMATIVE,
            Devoir.date_limite >= debut,
            Devoir.date_limite < fin,
        )
        .all()
    )

    notes: list[NoteDuBulletin] = []
    for devoir in sorted(devoirs, key=lambda d: d.date_limite):
        points_max_devoir = sum(q.points_max for q in devoir.questions) or 1.0
        soumission = (
            db.query(Soumission)
            .filter(Soumission.devoir_id == devoir.id, Soumission.eleve_id == eleve.id)
            .first()
        )
        date_limite = devoir.date_limite if devoir.date_limite.tzinfo else devoir.date_limite.replace(tzinfo=timezone.utc)
        devoir_clos = datetime.now(timezone.utc) > date_limite

        if soumission is None:
            if not devoir_clos:
                continue  # pas encore d'echeance passee : rien a compter pour l'instant
            note_normalisee, note_brute = 0.0, None
        elif soumission.statut == StatutSoumission.CORRIGEE and soumission.note is not None:
            note_normalisee, note_brute = (soumission.note / points_max_devoir) * 100, soumission.note
        else:
            continue  # echec_correction en attente de revision manuelle : exclu pour l'instant

        notes.append(NoteDuBulletin(devoir, note_brute, points_max_devoir, note_normalisee,
                                    _coefficient_pour(db, classe.niveau, devoir.matiere)))
    return notes


def moyennes_par_matiere(notes: list[tuple[str, float, float]]) -> list[tuple[str, float, float, int]]:
    """(matiere, moyenne sur 100, coefficient, nombre de devoirs), par ordre alphabetique."""
    par_matiere: dict[str, list[tuple[float, float]]] = {}
    for matiere, note, coefficient in notes:
        par_matiere.setdefault(matiere, []).append((note, coefficient))
    return [
        (matiere, sum(n for n, _ in lignes) / len(lignes), lignes[0][1], len(lignes))
        for matiere, lignes in sorted(par_matiere.items())
    ]


def _calculer_et_enregistrer_bulletin(db: Session, eleve: Eleve, classe_id: str, periode: str) -> Bulletin:
    """Moyenne generale PONDEREE des devoirs de la periode (voir notes_de_la_periode)."""
    existant = (
        db.query(Bulletin)
        .filter(Bulletin.eleve_id == eleve.id, Bulletin.classe_id == classe_id, Bulletin.periode == periode)
        .first()
    )
    if existant is not None and existant.valide_par_conseil:
        return existant  # fige des la deliberation : une correction ulterieure ne le modifie plus

    notes = notes_de_la_periode(db, eleve, classe_id, periode)
    poids_total = sum(c for _, _, c in notes)
    if poids_total == 0:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "aucun_devoir_evalue", "Aucun devoir clos et évalué pour cette période."
        )

    moyenne = sum(n * c for _, n, c in notes) / poids_total

    bulletin = (
        db.query(Bulletin)
        .filter(Bulletin.eleve_id == eleve.id, Bulletin.classe_id == classe_id, Bulletin.periode == periode)
        .first()
    )
    if bulletin is None:
        bulletin = Bulletin(eleve_id=eleve.id, classe_id=classe_id, periode=periode, moyenne_generale=moyenne)
        db.add(bulletin)
    else:
        bulletin.moyenne_generale = moyenne
    db.commit()
    db.refresh(bulletin)
    return bulletin


class PeriodeOut(BaseModel):
    code: str
    libelle: str
    debut: date
    fin: date
    courante: bool


@router.get("/classes/{classe_id}/periodes", response_model=list[PeriodeOut])
def periodes_de_la_classe(
    classe_id: str,
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(get_current_user),
) -> list[PeriodeOut]:
    """Trimestres (primaire, secondaire) ou semestres (universite) de l'annee de la classe,
    avec la periode en cours - pour les onglets du bulletin."""
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    etablissement = db.get(Etablissement, classe.etablissement_id)
    courante = periodes_evaluation.periode_de(datetime.now(timezone.utc), etablissement.type, classe.annee_academique)
    return [
        PeriodeOut(code=p.code, libelle=p.libelle, debut=p.debut, fin=p.fin, courante=p.code == courante.code)
        for p in periodes_evaluation.periodes(etablissement.type, classe.annee_academique)
    ]


_ROLES_BULLETIN = (
    RoleUtilisateur.ELEVE,
    RoleUtilisateur.TUTEUR,
    RoleUtilisateur.ENSEIGNANT,
    RoleUtilisateur.ADMIN_ETABLISSEMENT,
    RoleUtilisateur.ADMIN_MINISTERIEL,
)


@router.get("/eleves/{eleve_utilisateur_id}/bulletins", response_model=BulletinOut)
def obtenir_bulletin(
    eleve_utilisateur_id: str,
    classe_id: str,
    periode: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(*_ROLES_BULLETIN)),
) -> Bulletin:
    eleve, _ = _eleve_et_classe_du_bulletin(db, utilisateur, eleve_utilisateur_id, classe_id)
    return _calculer_et_enregistrer_bulletin(db, eleve, classe_id, periode)


@router.get("/eleves/{eleve_utilisateur_id}/bulletins/pdf")
def telecharger_bulletin_pdf(
    eleve_utilisateur_id: str,
    classe_id: str,
    periode: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(*_ROLES_BULLETIN)),
) -> Response:
    """Bulletin officiel d'une periode en PDF (moyennes par matiere, moyenne generale,
    decision du conseil). Memes droits que la consultation du bulletin."""
    eleve, classe = _eleve_et_classe_du_bulletin(db, utilisateur, eleve_utilisateur_id, classe_id)
    bulletin = _calculer_et_enregistrer_bulletin(db, eleve, classe_id, periode)
    evaluations = evaluations_de_la_periode(db, eleve, classe_id, periode)
    matieres = moyennes_par_matiere([(n.devoir.matiere, n.sur_100, n.coefficient) for n in evaluations])
    contenu = generer_pdf_bulletin(db, eleve, classe, bulletin, matieres, evaluations)
    nom = f"bulletin-{periode}-{(eleve.matricule or eleve.nom).lower()}.pdf"
    return Response(contenu, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{nom}"'})


def _eleve_et_classe_du_bulletin(
    db: Session, utilisateur: Utilisateur, eleve_utilisateur_id: str, classe_id: str
) -> tuple[Eleve, Classe]:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Élève introuvable.")
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")

    if utilisateur.role == RoleUtilisateur.ELEVE and utilisateur.id != eleve_utilisateur_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce bulletin ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.TUTEUR and eleve.tuteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet élève n'est pas rattaché à votre compte.")
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        _verifier_enseignant_rattache(db, utilisateur, classe.id)
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        lien = db.get(AdminEtablissement, utilisateur.id)
        if lien is None or lien.etablissement_id != classe.etablissement_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet établissement.")

    # Le bulletin est ecrit en base et remonte dans le dossier scolaire national de
    # l'eleve (vie scolaire) : jamais pour une classe dans laquelle il n'est pas inscrit.
    inscrit = (
        db.query(Inscription)
        .filter(
            Inscription.eleve_id == eleve.id,
            Inscription.classe_id == classe_id,
            Inscription.statut == StatutInscription.VALIDEE,
        )
        .first()
    )
    if inscrit is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Cet élève n'est pas inscrit dans cette classe.")
    return eleve, classe


@router.post("/bulletins/{bulletin_id}/valider-passage", response_model=BulletinOut)
def valider_passage(
    bulletin_id: str,
    payload: ValiderPassageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
    files_client: LuluFilesClient = Depends(get_files_client),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Bulletin:
    """UC-09 : le calcul automatique ne decide jamais seul d'une decision lourde
    (passage/redoublement/diplome) - toujours une action humaine explicite. Portee
    verifiee ici (auparavant absente : n'importe quel enseignant authentifie pouvait
    valider le passage d'un eleve d'un etablissement totalement different)."""
    bulletin = db.get(Bulletin, bulletin_id)
    if bulletin is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Bulletin introuvable.")
    classe = db.get(Classe, bulletin.classe_id)
    _verifier_enseignant_rattache(db, enseignant, classe.id)

    bulletin.decision_passage = payload.decision
    bulletin.valide_par_conseil = True
    db.commit()
    db.refresh(bulletin)
    # Decision favorable : les certificats de reussite deja demandes (et payes) par l'eleve
    # sont generes et livres sans attendre l'A+.
    if est_favorable(bulletin.decision_passage):
        en_attente = (
            db.query(DemandeActeAcademique.id)
            .join(TypeActeAcademique, TypeActeAcademique.id == DemandeActeAcademique.type_acte_id)
            .filter(
                DemandeActeAcademique.eleve_id == bulletin.eleve_id,
                DemandeActeAcademique.statut == StatutDemandeActe.EN_TRAITEMENT,
                TypeActeAcademique.modele_document == CERTIFICAT_REUSSITE,
            )
            .all()
        )
        for (demande_id,) in en_attente:
            background_tasks.add_task(livrer_en_arriere_plan, session_factory, demande_id, files_client)
    return bulletin


def _devoir_vers_admin_out(
    devoir: Devoir, etablissement_id: str, etablissement_nom: str, enseignant: Utilisateur
) -> AdminDevoirOut:
    return AdminDevoirOut(
        id=devoir.id,
        titre=devoir.titre,
        matiere=devoir.matiere,
        classe_id=devoir.classe_id,
        etablissement_id=etablissement_id,
        etablissement_nom=etablissement_nom,
        enseignant_id=devoir.enseignant_id,
        enseignant_nom=enseignant.nom,
        enseignant_prenom=enseignant.prenom,
        masque=devoir.masque_par_id is not None,
        created_at=devoir.created_at,
    )


@router.get("/admin/devoirs", response_model=AdminDevoirPageOut)
def lister_devoirs_supervision(
    etablissement_id: str | None = None,
    enseignant_id: str | None = None,
    masque: bool | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> AdminDevoirPageOut:
    """UC-37/53 : meme raisonnement que GET /admin/cours (pedagogie) - supervision
    transverse, pagination serveur obligatoire."""
    limit = max(1, min(limit, 60))
    offset = max(0, offset)

    requete = db.query(Devoir).join(Classe, Devoir.classe_id == Classe.id)
    if etablissement_id:
        requete = requete.filter(Classe.etablissement_id == etablissement_id)
    if enseignant_id:
        requete = requete.filter(Devoir.enseignant_id == enseignant_id)
    if masque is not None:
        requete = requete.filter(Devoir.masque_par_id.isnot(None) if masque else Devoir.masque_par_id.is_(None))

    total = requete.with_entities(func.count(Devoir.id)).scalar() or 0
    page = requete.order_by(Devoir.created_at.desc()).offset(offset).limit(limit).all()

    classe_par_id = {
        c.id: c for c in db.query(Classe).filter(Classe.id.in_({devoir.classe_id for devoir in page}))
    } if page else {}
    etablissement_ids = {c.etablissement_id for c in classe_par_id.values()}
    etablissements = {
        e.id: e.nom for e in db.query(Etablissement).filter(Etablissement.id.in_(etablissement_ids)).all()
    } if etablissement_ids else {}
    enseignant_ids = {devoir.enseignant_id for devoir in page}
    enseignants = {
        u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_(enseignant_ids)).all()
    } if enseignant_ids else {}

    items = [
        _devoir_vers_admin_out(
            devoir,
            classe_par_id[devoir.classe_id].etablissement_id,
            etablissements.get(classe_par_id[devoir.classe_id].etablissement_id, ""),
            enseignants[devoir.enseignant_id],
        )
        for devoir in page
    ]
    return AdminDevoirPageOut(items=items, total=total, limit=limit, offset=offset)


@router.post("/devoirs/{devoir_id}/masquer", response_model=DevoirOut)
def masquer_devoir(
    devoir_id: str,
    payload: MasquerContenuRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Devoir:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    if devoir.masque_par_id is not None:
        raise api_error(status.HTTP_409_CONFLICT, "deja_masque", "Ce devoir est déjà masqué.")

    devoir.masque_par_id = admin.id
    devoir.masque_le = datetime.now(timezone.utc)
    journaliser_action_ministerielle(db, admin, "devoir.masquer", "devoir", devoir.id, payload.motif)
    db.commit()
    db.refresh(devoir)
    return devoir


@router.post("/devoirs/{devoir_id}/demasquer", response_model=DevoirOut)
def demasquer_devoir(
    devoir_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Devoir:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    if devoir.masque_par_id is None:
        raise api_error(status.HTTP_409_CONFLICT, "pas_masque", "Ce devoir n'est pas masqué.")

    devoir.masque_par_id = None
    devoir.masque_le = None
    journaliser_action_ministerielle(db, admin, "devoir.demasquer", "devoir", devoir.id, None)
    db.commit()
    db.refresh(devoir)
    return devoir
