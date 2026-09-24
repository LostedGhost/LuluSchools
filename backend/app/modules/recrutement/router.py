import hashlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import api_error, get_current_user, require_roles
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
    ContratSignerRequest,
    PosteCreate,
    PosteOut,
    PropositionReconductionOut,
    ReconductionCreate,
)

CONTESTATION_DELAI_JOURS = 5
CASIER_JUDICIAIRE_RETENTION_JOURS = 30
RECONDUCTION_FENETRE_JOURS = 30

router = APIRouter(tags=["recrutement"])


def _verifier_admin_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    if utilisateur.role != RoleUtilisateur.ADMIN_ETABLISSEMENT:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action.")
    lien = db.get(AdminEtablissement, utilisateur.id)
    if lien is None or lien.etablissement_id != etablissement_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")


@router.post(
    "/etablissements/{etablissement_id}/postes", response_model=PosteOut, status_code=status.HTTP_201_CREATED
)
def creer_poste(
    etablissement_id: str,
    payload: PosteCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_user),
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


@router.post(
    "/postes/{poste_id}/candidatures", response_model=CandidatureOut, status_code=status.HTTP_201_CREATED
)
def postuler(
    poste_id: str,
    types: list[str] = Form(...),
    fichiers: list[UploadFile] = File(...),
    casier_judiciaire: UploadFile = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    llm_client: FreeLLMClient = Depends(get_llm_client),
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
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "documents_incomplets",
            "Les documents fournis ne correspondent pas exactement aux criteres du poste.",
        )

    candidature = Candidature(
        poste_id=poste_id, enseignant_id=enseignant.id, statut=StatutCandidature.EN_EVALUATION
    )
    db.add(candidature)
    db.flush()

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
        try:
            image_bytes, image_content_type = convertir_en_image(
                contenu, fichier.content_type or "application/octet-stream"
            )
            note = llm_client.noter_document(
                image_bytes, image_content_type, critere=f"conformite du document '{type_document}'"
            )
            document.note_ia = note
            document.statut = StatutDocument.NOTE
        except DocumentScoringError:
            document.statut = StatutDocument.ECHEC_NOTATION
        db.add(document)

    contenu_casier = casier_judiciaire.file.read()
    dossier_casier = Path(settings.casier_judiciaire_storage_path)
    dossier_casier.mkdir(parents=True, exist_ok=True)
    extension = Path(casier_judiciaire.filename or "").suffix or ".bin"
    chemin_casier = dossier_casier / f"{candidature.id}{extension}"
    chemin_casier.write_bytes(contenu_casier)
    db.add(
        VerificationCasierJudiciaire(
            candidature_id=candidature.id,
            chemin_fichier_local=str(chemin_casier),
            statut=StatutVerificationCasier.EN_ATTENTE,
        )
    )

    db.flush()
    documents = db.query(DocumentCandidature).filter(DocumentCandidature.candidature_id == candidature.id).all()

    if any(d.statut == StatutDocument.ECHEC_NOTATION for d in documents):
        # Aucune decision automatique tant qu'un document n'a pas pu etre note (ADR-002) :
        # reste en_evaluation en attente d'une revision manuelle (endpoint pas encore construit).
        pass
    else:
        sous_seuil = any(d.note_ia < criteres_par_type[d.type_document].seuil_minimal for d in documents)
        if sous_seuil:
            candidature.statut = StatutCandidature.REJETEE
        else:
            poids_total = sum(criteres_par_type[d.type_document].coefficient for d in documents)
            candidature.score = (
                sum(d.note_ia * criteres_par_type[d.type_document].coefficient for d in documents)
                / poids_total
            )

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
    if datetime.now(timezone.utc) - candidature.created_at.replace(tzinfo=timezone.utc) > timedelta(
        days=CONTESTATION_DELAI_JOURS
    ):
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
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> Contestation:
    contestation = db.get(Contestation, contestation_id)
    if contestation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contestation introuvable.")

    candidature = db.get(Candidature, contestation.candidature_id)
    poste = db.get(Poste, candidature.poste_id)
    _verifier_admin_de_l_etablissement(db, admin, poste.etablissement_id)

    if payload.decision == StatutContestation.REJETEE and not payload.motif_decision:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "motif_requis", "Un motif est requis en cas de rejet."
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
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
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
    payload: ContratSignerRequest,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Contrat:
    """Signature electronique SIMPLE (horodatage + hash du document), pas encore la
    signature qualifiee prevue par l'utilisateur pour la V1 : aucun prestataire de
    certification n'a ete choisi a ce jour (point ouvert, voir rapport final)."""
    contrat = db.get(Contrat, contrat_id)
    if contrat is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contrat introuvable.")
    if contrat.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce contrat ne vous appartient pas.")
    if contrat.statut != StatutContrat.EN_ATTENTE_SIGNATURE:
        raise api_error(status.HTTP_409_CONFLICT, "deja_signe", "Ce contrat est deja signe.")
    if payload.nom_tape.strip().lower() != f"{enseignant.prenom} {enseignant.nom}".strip().lower():
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "nom_incorrect",
            "Le nom tape ne correspond pas au titulaire du compte.",
        )

    contrat.signature_horodatage = datetime.now(timezone.utc)
    contrat.signature_hash_document = hashlib.sha256(contrat.syllabus.encode("utf-8")).hexdigest()
    contrat.statut = StatutContrat.SIGNE
    db.commit()
    db.refresh(contrat)
    return contrat


@router.post(
    "/contrats/{contrat_id}/reconduction",
    response_model=PropositionReconductionOut,
    status_code=status.HTTP_201_CREATED,
)
def proposer_reconduction(
    contrat_id: str,
    payload: ReconductionCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
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
