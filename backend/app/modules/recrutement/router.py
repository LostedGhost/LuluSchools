import hashlib
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session, sessionmaker

from app.core.crypto import chiffrer_bytes
from app.core.database import get_db, get_session_factory
from app.core.deps import (
    api_error,
    get_current_active_user,
    get_current_user,
    require_roles,
    verifier_portee_etablissement,
)
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.core.llm import DocumentScoringError, FreeLLMClient, get_llm_client
from app.modules.etablissements.models import AdminEtablissement, Etablissement
from app.modules.identite.models import Enseignant, RoleUtilisateur, Utilisateur
from app.modules.recrutement.conversion import convertir_en_image
from app.modules.recrutement.models import (
    Candidature,
    Contestation,
    Contrat,
    CritereDocumentPoste,
    DocumentCandidature,
    Poste,
    PropositionReconduction,
    StatutCandidature,
    StatutContestation,
    StatutContrat,
    StatutDocument,
    StatutPoste,
    StatutProposition,
    StatutVerificationCasier,
    VerificationCasierJudiciaire,
)
from app.modules.recrutement.schemas import (
    CandidatureOut,
    ContestationCreate,
    ContestationDecisionRequest,
    ContestationOut,
    ContratCreate,
    ContratOut,
    LienFichierOut,
    NotationManuelleRequest,
    PosteCreate,
    PosteOut,
    PropositionReconductionOut,
    ReconductionCreate,
)

CONTESTATION_DELAI_JOURS = 5
CASIER_JUDICIAIRE_RETENTION_JOURS = 30
RECONDUCTION_FENETRE_JOURS = 30

router = APIRouter(tags=["recrutement"])


def _ajouter_jours_ouvres(date_depart: datetime, jours_ouvres: int) -> datetime:
    """UC-04b exige un delai en jours OUVRES (lundi-vendredi), pas calendaires."""
    resultat = date_depart
    ajoutes = 0
    while ajoutes < jours_ouvres:
        resultat += timedelta(days=1)
        if resultat.weekday() < 5:  # 0=lundi ... 6=dimanche
            ajoutes += 1
    return resultat


def _verifier_admin_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    verifier_portee_etablissement(db, utilisateur, etablissement_id)


@router.post(
    "/etablissements/{etablissement_id}/postes", response_model=PosteOut, status_code=status.HTTP_201_CREATED
)
def creer_poste(
    etablissement_id: str,
    payload: PosteCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> Poste:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    _verifier_admin_de_l_etablissement(db, utilisateur, etablissement_id)

    poste = Poste(etablissement_id=etablissement_id, titre=payload.titre, statut=StatutPoste.OUVERT)
    db.add(poste)
    db.flush()
    for critere in payload.criteres:
        db.add(
            CritereDocumentPoste(
                poste_id=poste.id,
                type_document=critere.type_document,
                coefficient=critere.coefficient,
                seuil_minimal=critere.seuil_minimal,
            )
        )
    db.commit()
    db.refresh(poste)
    return poste


@router.get("/postes/{poste_id}", response_model=PosteOut)
def obtenir_poste(
    poste_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(get_current_user)
) -> Poste:
    poste = db.get(Poste, poste_id)
    if poste is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Poste introuvable.")
    return poste


@router.get("/etablissements/{etablissement_id}/postes", response_model=list[PosteOut])
def lister_postes(
    etablissement_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(get_current_user)
) -> list[Poste]:
    """Sans cette liste, un enseignant candidat n'a aucun moyen de decouvrir les postes
    ouverts d'un etablissement sans deja en connaitre les id (UC-04)."""
    return db.query(Poste).filter(Poste.etablissement_id == etablissement_id).all()


@router.get("/mes-candidatures", response_model=list[CandidatureOut])
def mes_candidatures(
    db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> list[Candidature]:
    return db.query(Candidature).filter(Candidature.enseignant_id == enseignant.id).all()


@router.get("/mes-contrats", response_model=list[ContratOut])
def mes_contrats(
    db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> list[Contrat]:
    return db.query(Contrat).filter(Contrat.enseignant_id == enseignant.id).all()


@router.get("/etablissements/{etablissement_id}/contestations-en-attente", response_model=list[ContestationOut])
def contestations_en_attente(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[Contestation]:
    _verifier_admin_de_l_etablissement(db, admin, etablissement_id)
    return (
        db.query(Contestation)
        .join(Candidature, Candidature.id == Contestation.candidature_id)
        .join(Poste, Poste.id == Candidature.poste_id)
        .filter(Poste.etablissement_id == etablissement_id, Contestation.statut == StatutContestation.EN_ATTENTE)
        .order_by(Contestation.created_at.asc())
        .all()
    )


@router.get("/postes/{poste_id}/candidatures", response_model=list[CandidatureOut])
def lister_candidatures_du_poste(
    poste_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[Candidature]:
    """Sans cette liste, l'A+ n'a aucun moyen de retrouver les candidatures d'un poste
    pour decider d'un contrat (UC-04, UC-05) sans deja en connaitre les id."""
    poste = db.get(Poste, poste_id)
    if poste is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Poste introuvable.")
    _verifier_admin_de_l_etablissement(db, admin, poste.etablissement_id)
    return db.query(Candidature).filter(Candidature.poste_id == poste_id).all()


@router.post(
    "/postes/{poste_id}/candidatures", response_model=CandidatureOut, status_code=status.HTTP_201_CREATED
)
def postuler(
    poste_id: str,
    background_tasks: BackgroundTasks,
    types: list[str] = Form(...),
    fichiers: list[UploadFile] = File(...),
    casier_judiciaire: UploadFile = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    session_factory: sessionmaker = Depends(get_session_factory),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Candidature:
    poste = db.get(Poste, poste_id)
    if poste is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Poste introuvable.")
    if poste.statut != StatutPoste.OUVERT:
        raise api_error(status.HTTP_409_CONFLICT, "poste_ferme", "Ce poste n'accepte plus de candidatures.")

    criteres_par_type = {c.type_document: c for c in poste.criteres}
    if len(types) != len(fichiers) or set(types) != set(criteres_par_type.keys()):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "documents_incomplets",
            "Les documents fournis ne correspondent pas exactement aux criteres du poste.",
        )

    candidature = Candidature(
        poste_id=poste_id, enseignant_id=enseignant.id, statut=StatutCandidature.EN_EVALUATION
    )
    db.add(candidature)
    db.flush()

    documents_a_noter = []
    for type_document, fichier in zip(types, fichiers):
        contenu = fichier.file.read()
        try:
            lulufiles_file_id = files_client.upload(
                contenu, fichier.filename or type_document, fichier.content_type or "application/octet-stream"
            )
        except FileStorageError as exc:
            db.rollback()
            raise api_error(
                status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible de stocker un document, veuillez reessayer."
            ) from exc

        document = DocumentCandidature(
            candidature_id=candidature.id,
            type_document=type_document,
            lulufiles_file_id=lulufiles_file_id,
            statut=StatutDocument.EN_ATTENTE,
        )
        db.add(document)
        db.flush()

        # Conversion locale (PyMuPDF, pas de reseau) : reste synchrone, rapide et
        # deterministe. Seul l'appel reseau vers FreeLLM (noter_document, potentiellement
        # plusieurs secondes x N documents, ADR-002 sans SLA) part en arriere-plan.
        image_bytes, image_content_type = convertir_en_image(
            contenu, fichier.content_type or "application/octet-stream"
        )
        documents_a_noter.append(
            {
                "document_id": document.id,
                "image_bytes": image_bytes,
                "image_content_type": image_content_type,
                "type_document": type_document,
            }
        )

    contenu_casier = casier_judiciaire.file.read()
    db.add(
        VerificationCasierJudiciaire(
            candidature_id=candidature.id,
            contenu_chiffre=chiffrer_bytes(contenu_casier),
            nom_fichier=casier_judiciaire.filename or f"{candidature.id}.bin",
            statut=StatutVerificationCasier.EN_ATTENTE,
        )
    )

    db.commit()
    db.refresh(candidature)

    background_tasks.add_task(
        _noter_candidature_en_arriere_plan, candidature.id, documents_a_noter, llm_client, session_factory
    )
    return candidature


def _noter_candidature_en_arriere_plan(
    candidature_id: str, documents_a_noter: list[dict], llm_client: FreeLLMClient, session_factory: sessionmaker
) -> None:
    """Execute apres l'envoi de la reponse HTTP (voir BackgroundTasks sur postuler) :
    ouvre sa propre session DB via session_factory (celle de la requete est deja fermee).
    llm_client et session_factory sont ceux deja resolus par Depends au moment de la
    requete (donc les fakes injectes par les tests en environnement de test), jamais
    reconstruits ici - pas d'appel reseau reel ni de moteur DB different hors de ceux-la."""
    db = session_factory()
    try:
        for item in documents_a_noter:
            document = db.get(DocumentCandidature, item["document_id"])
            if document is None:
                continue
            try:
                note = llm_client.noter_document(
                    item["image_bytes"], item["image_content_type"],
                    critere=f"conformite du document '{item['type_document']}'",
                )
                document.note_ia = note
                document.statut = StatutDocument.NOTE
            except DocumentScoringError:
                document.statut = StatutDocument.ECHEC_NOTATION
        db.commit()

        candidature = db.get(Candidature, candidature_id)
        poste = db.get(Poste, candidature.poste_id)
        criteres_par_type = {c.type_document: c for c in poste.criteres}
        _reevaluer_candidature(db, candidature, criteres_par_type)
        db.commit()
    finally:
        db.close()


def _reevaluer_candidature(db: Session, candidature: Candidature, criteres_par_type: dict) -> None:
    """Applique la decision d'elimination/score une fois tous les documents notes.
    Reutilisee a la soumission initiale et apres une revision manuelle (ADR-002 :
    aucune decision automatique tant qu'un document n'a pas pu etre note)."""
    documents = db.query(DocumentCandidature).filter(DocumentCandidature.candidature_id == candidature.id).all()

    if any(d.statut == StatutDocument.ECHEC_NOTATION for d in documents):
        return  # en attente de revision manuelle, voir POST /documents-candidature/{id}/noter-manuellement

    sous_seuil = any(d.note_ia < criteres_par_type[d.type_document].seuil_minimal for d in documents)
    if sous_seuil:
        candidature.statut = StatutCandidature.REJETEE
    else:
        poids_total = sum(criteres_par_type[d.type_document].coefficient for d in documents)
        candidature.score = (
            sum(d.note_ia * criteres_par_type[d.type_document].coefficient for d in documents) / poids_total
        )


@router.get("/candidatures/en-attente-revision", response_model=list[CandidatureOut])
def lister_candidatures_en_attente_revision(
    db: Session = Depends(get_db), admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL))
) -> list[Candidature]:
    """Ecran de revision manuelle (recrutement) : candidatures ayant au moins un
    document que FreeLLM n'a pas pu noter, scopees aux etablissements administres."""
    lien = db.get(AdminEtablissement, admin.id)
    if lien is None:
        return []
    return (
        db.query(Candidature)
        .join(Poste, Poste.id == Candidature.poste_id)
        .join(DocumentCandidature, DocumentCandidature.candidature_id == Candidature.id)
        .filter(Poste.etablissement_id == lien.etablissement_id, DocumentCandidature.statut == StatutDocument.ECHEC_NOTATION)
        .distinct()
        .all()
    )


@router.post("/documents-candidature/{document_id}/noter-manuellement", response_model=CandidatureOut)
def noter_document_manuellement(
    document_id: str,
    payload: NotationManuelleRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Candidature:
    document = db.get(DocumentCandidature, document_id)
    if document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Document introuvable.")
    candidature = db.get(Candidature, document.candidature_id)
    poste = db.get(Poste, candidature.poste_id)
    _verifier_admin_de_l_etablissement(db, admin, poste.etablissement_id)

    if document.statut != StatutDocument.ECHEC_NOTATION:
        raise api_error(status.HTTP_409_CONFLICT, "revision_non_requise", "Ce document n'attend pas de revision manuelle.")

    document.note_ia = payload.note
    document.statut = StatutDocument.NOTE
    db.flush()

    criteres_par_type = {c.type_document: c for c in poste.criteres}
    _reevaluer_candidature(db, candidature, criteres_par_type)

    db.commit()
    db.refresh(candidature)
    return candidature


@router.get("/candidatures/{candidature_id}", response_model=CandidatureOut)
def obtenir_candidature(
    candidature_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_user)
) -> Candidature:
    candidature = db.get(Candidature, candidature_id)
    if candidature is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Candidature introuvable.")

    if utilisateur.role == RoleUtilisateur.ENSEIGNANT and candidature.enseignant_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette candidature ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        poste = db.get(Poste, candidature.poste_id)
        _verifier_admin_de_l_etablissement(db, utilisateur, poste.etablissement_id)

    return candidature


@router.get("/documents-candidature/{document_id}/lien", response_model=LienFichierOut)
def obtenir_lien_document_candidature(
    document_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(get_current_user),
) -> LienFichierOut:
    """Bug reel corrige : ni le candidat ni l'A+ n'avaient jusqu'ici de moyen de
    consulter le document lui-meme (seule la note IA etait exposee) - rend l'ecran de
    revision manuelle (UC-04) et la verification d'un A+ effectivement utilisables."""
    document = db.get(DocumentCandidature, document_id)
    if document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Document introuvable.")
    candidature = db.get(Candidature, document.candidature_id)
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT and candidature.enseignant_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce document ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        poste = db.get(Poste, candidature.poste_id)
        _verifier_admin_de_l_etablissement(db, utilisateur, poste.etablissement_id)
    if not document.lulufiles_file_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ce document n'a pas de fichier associe.")

    try:
        url = files_client.get_signed_link(document.lulufiles_file_id, disposition="inline")
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible d'obtenir le lien du fichier, veuillez reessayer."
        ) from exc
    return LienFichierOut(url=url)


@router.post(
    "/candidatures/{candidature_id}/contestation",
    response_model=ContestationOut,
    status_code=status.HTTP_201_CREATED,
)
def contester_candidature(
    candidature_id: str,
    payload: ContestationCreate,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Contestation:
    candidature = db.get(Candidature, candidature_id)
    if candidature is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Candidature introuvable.")
    if candidature.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette candidature ne vous appartient pas.")
    if candidature.statut != StatutCandidature.REJETEE:
        raise api_error(
            status.HTTP_409_CONFLICT, "candidature_non_rejetee", "Seule une candidature rejetee peut etre contestee."
        )
    limite = _ajouter_jours_ouvres(candidature.created_at.replace(tzinfo=timezone.utc), CONTESTATION_DELAI_JOURS)
    if datetime.now(timezone.utc) > limite:
        raise api_error(status.HTTP_409_CONFLICT, "delai_depasse", "Le delai de contestation est depasse.")

    contestation = Contestation(candidature_id=candidature_id, motif=payload.motif)
    candidature.statut = StatutCandidature.EN_EVALUATION
    db.add(contestation)
    db.commit()
    db.refresh(contestation)
    return contestation


@router.post("/contestations/{contestation_id}/decision", response_model=ContestationOut)
def decider_contestation(
    contestation_id: str,
    payload: ContestationDecisionRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Contestation:
    contestation = db.get(Contestation, contestation_id)
    if contestation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contestation introuvable.")

    candidature = db.get(Candidature, contestation.candidature_id)
    poste = db.get(Poste, candidature.poste_id)
    _verifier_admin_de_l_etablissement(db, admin, poste.etablissement_id)

    if payload.decision == StatutContestation.REJETEE and not payload.motif_decision:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "motif_requis", "Un motif est requis en cas de rejet."
        )

    contestation.statut = payload.decision
    contestation.motif_decision = payload.motif_decision
    contestation.decided_at = datetime.now(timezone.utc)
    if payload.decision == StatutContestation.REJETEE:
        candidature.statut = StatutCandidature.REJETEE

    db.commit()
    db.refresh(contestation)
    return contestation


@router.post(
    "/candidatures/{candidature_id}/contrat", response_model=ContratOut, status_code=status.HTTP_201_CREATED
)
def creer_contrat(
    candidature_id: str,
    payload: ContratCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Contrat:
    candidature = db.get(Candidature, candidature_id)
    if candidature is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Candidature introuvable.")
    poste = db.get(Poste, candidature.poste_id)
    _verifier_admin_de_l_etablissement(db, admin, poste.etablissement_id)

    if candidature.statut != StatutCandidature.EN_EVALUATION or candidature.score is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "candidature_non_eligible",
            "Cette candidature n'est pas eligible a un contrat (score manquant ou statut invalide).",
        )

    contrat = Contrat(
        candidature_id=candidature_id,
        enseignant_id=candidature.enseignant_id,
        etablissement_id=poste.etablissement_id,
        syllabus=payload.syllabus,
        date_fin=payload.date_fin,
        statut=StatutContrat.EN_ATTENTE_SIGNATURE,
    )
    candidature.statut = StatutCandidature.RETENUE
    poste.statut = StatutPoste.POURVU
    db.add(contrat)
    db.commit()
    db.refresh(contrat)
    return contrat


@router.post("/contrats/{contrat_id}/signer", response_model=ContratOut)
def signer_contrat(
    contrat_id: str,
    signature_image: UploadFile = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Contrat:
    """Signature electronique SIMPLE (Art. 284-285 de la loi n. 2017-20 : admise, mais
    preuve plus faible qu'une signature qualifiee en cas de litige devant un tribunal -
    aucun prestataire de certification qualifiee n'a ete retenu). Concretement : un trace
    dessine au doigt/stylet sur un canvas cote client, exporte en PNG, envoye ici et
    stocke via LuluFiles. L'horodatage + le hash du contrat au moment de la signature
    forment la piste d'audit (voir ADR-004)."""
    contrat = db.get(Contrat, contrat_id)
    if contrat is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contrat introuvable.")
    if contrat.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce contrat ne vous appartient pas.")
    if contrat.statut != StatutContrat.EN_ATTENTE_SIGNATURE:
        raise api_error(status.HTTP_409_CONFLICT, "deja_signe", "Ce contrat est deja signe.")

    contenu_image = signature_image.file.read()
    if not contenu_image:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "signature_vide", "Aucun trace de signature recu.")
    try:
        signature_image_id = files_client.upload(
            contenu_image, signature_image.filename or "signature.png", signature_image.content_type or "image/png"
        )
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible de stocker la signature, veuillez reessayer."
        ) from exc

    contrat.signature_horodatage = datetime.now(timezone.utc)
    contrat.signature_hash_document = hashlib.sha256(contrat.syllabus.encode("utf-8")).hexdigest()
    contrat.signature_image_lulufiles_id = signature_image_id
    contrat.statut = StatutContrat.SIGNE
    db.commit()
    db.refresh(contrat)
    return contrat


@router.get("/contrats/{contrat_id}/lien-signature", response_model=LienFichierOut)
def obtenir_lien_signature_contrat(
    contrat_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(get_current_user),
) -> LienFichierOut:
    contrat = db.get(Contrat, contrat_id)
    if contrat is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contrat introuvable.")
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT and contrat.enseignant_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce contrat ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        _verifier_admin_de_l_etablissement(db, utilisateur, contrat.etablissement_id)
    if not contrat.signature_image_lulufiles_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ce contrat n'est pas encore signe.")

    try:
        url = files_client.get_signed_link(contrat.signature_image_lulufiles_id, disposition="inline")
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible d'obtenir le lien du fichier, veuillez reessayer."
        ) from exc
    return LienFichierOut(url=url)


@router.post(
    "/contrats/{contrat_id}/reconduction",
    response_model=PropositionReconductionOut,
    status_code=status.HTTP_201_CREATED,
)
def proposer_reconduction(
    contrat_id: str,
    payload: ReconductionCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> PropositionReconduction:
    """UC-05b. L'enseignant doit re-signer integralement (pas de reconduction tacite) :
    cree un nouveau Contrat en attente de signature via POST /contrats/{id}/signer."""
    contrat = db.get(Contrat, contrat_id)
    if contrat is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contrat introuvable.")
    _verifier_admin_de_l_etablissement(db, admin, contrat.etablissement_id)

    if contrat.statut != StatutContrat.SIGNE:
        raise api_error(
            status.HTTP_409_CONFLICT, "contrat_non_signe", "Seul un contrat signe peut etre reconduit."
        )
    if (contrat.date_fin - date.today()).days > RECONDUCTION_FENETRE_JOURS:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "hors_fenetre",
            f"La reconduction n'est possible que dans les {RECONDUCTION_FENETRE_JOURS} jours avant l'echeance.",
        )

    nouveau_contrat = Contrat(
        candidature_id=contrat.candidature_id,
        enseignant_id=contrat.enseignant_id,
        etablissement_id=contrat.etablissement_id,
        syllabus=payload.syllabus,
        date_fin=payload.date_fin,
        statut=StatutContrat.EN_ATTENTE_SIGNATURE,
    )
    db.add(nouveau_contrat)
    db.flush()

    proposition = PropositionReconduction(
        contrat_precedent_id=contrat.id,
        nouveau_contrat_id=nouveau_contrat.id,
        statut=StatutProposition.EN_ATTENTE,
    )
    db.add(proposition)
    db.commit()
    db.refresh(proposition)
    return proposition
