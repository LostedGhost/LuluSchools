import hashlib
from datetime import date, datetime, timedelta, timezone

import logging
import mimetypes

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from cryptography.fernet import InvalidToken

from app.core.crypto import chiffrer_bytes, dechiffrer_bytes
from app.core.database import get_db, get_session_factory
from app.core.deps import (
    api_error,
    get_current_active_user,
    require_roles,
    verifier_portee_etablissement,
)
from app.core.conversion import convertir_en_image
from app.core.files import (
    MO,
    TYPES_DOCUMENT,
    TYPES_IMAGE,
    FileStorageError,
    LuluFilesClient,
    get_files_client,
    lire_upload_borne,
)
from app.core.formulaire import valider_reponses_formulaire
from app.core.llm import DocumentScoringError, FreeLLMClient, get_llm_client
from app.modules.etablissements.models import AdminEtablissement, Etablissement
from app.modules.identite.models import Enseignant, RoleUtilisateur, Utilisateur
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
    ContratAvecEnseignantOut,
    ContratCreate,
    ContratOut,
    EnseignantSigneOut,
    VerdictCasierRequest,
    VerificationCasierOut,
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
MAX_DOCUMENT_CANDIDATURE_OCTETS = 10 * MO
MAX_DOCUMENTS_CANDIDATURE = 15
MAX_SIGNATURE_OCTETS = 2 * MO

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recrutement"])


def purger_casiers_expires(db: Session) -> int:
    """Art. 395 : le contenu brut d'un casier n'est jamais conserve au-dela de la duree
    de retention, meme sans verdict - seul le statut reste. Appelee au demarrage du
    service (qui redemarre souvent sur le plan gratuit) et a chaque consultation."""
    maintenant = datetime.now(timezone.utc)
    expires = (
        db.query(VerificationCasierJudiciaire)
        .filter(
            VerificationCasierJudiciaire.contenu_chiffre.isnot(None),
            VerificationCasierJudiciaire.date_suppression_prevue.isnot(None),
            VerificationCasierJudiciaire.date_suppression_prevue < maintenant,
        )
        .all()
    )
    for verification in expires:
        verification.contenu_chiffre = None
    if expires:
        db.commit()
    return len(expires)


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

    poste = Poste(
        etablissement_id=etablissement_id,
        titre=payload.titre,
        description=payload.description,
        matiere=payload.matiere,
        remuneration_min=payload.remuneration_min,
        remuneration_max=payload.remuneration_max,
        schema_formulaire=[c.model_dump() for c in payload.schema_formulaire] if payload.schema_formulaire else None,
        statut=StatutPoste.OUVERT,
    )
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
    poste_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(get_current_active_user)
) -> Poste:
    poste = db.get(Poste, poste_id)
    if poste is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Poste introuvable.")
    return poste


@router.get("/etablissements/{etablissement_id}/postes", response_model=list[PosteOut])
def lister_postes(
    etablissement_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(get_current_active_user)
) -> list[Poste]:
    """Sans cette liste, un enseignant candidat n'a aucun moyen de decouvrir les postes
    ouverts d'un etablissement sans deja en connaitre les id (UC-04)."""
    return db.query(Poste).filter(Poste.etablissement_id == etablissement_id).all()


@router.get("/etablissements/{etablissement_id}/enseignants", response_model=list[EnseignantSigneOut])
def rechercher_enseignants_signes(
    etablissement_id: str,
    q: str | None = None,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[Utilisateur]:
    """Recherche par nom/prenom des enseignants ayant un contrat SIGNE avec cet
    etablissement - sert a l'affectation enseignant<->classe (voir
    etablissements/router.py), qui exigeait jusqu'ici de connaitre l'id brut de
    l'enseignant faute d'un tel endpoint."""
    verifier_portee_etablissement(db, admin, etablissement_id)
    requete = (
        db.query(Utilisateur)
        .join(Contrat, Contrat.enseignant_id == Utilisateur.id)
        .filter(Contrat.etablissement_id == etablissement_id, Contrat.statut == StatutContrat.SIGNE)
        .distinct()
    )
    if q and q.strip():
        motif = f"%{q.strip()}%"
        requete = requete.filter(or_(Utilisateur.nom.ilike(motif), Utilisateur.prenom.ilike(motif)))
    return requete.order_by(Utilisateur.nom.asc()).limit(20).all()


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


@router.get("/etablissements/{etablissement_id}/contrats", response_model=list[ContratAvecEnseignantOut])
def lister_contrats_etablissement(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[ContratAvecEnseignantOut]:
    """Sans cette liste, l'admin n'a aucun moyen de retrouver les contrats de son
    etablissement pour proposer une reconduction (UC-05b) sans deja connaitre leur id."""
    verifier_portee_etablissement(db, admin, etablissement_id)
    lignes = (
        db.query(Contrat, Utilisateur.nom, Utilisateur.prenom)
        .join(Utilisateur, Utilisateur.id == Contrat.enseignant_id)
        .filter(Contrat.etablissement_id == etablissement_id)
        .order_by(Contrat.date_fin.asc())
        .all()
    )
    return [
        ContratAvecEnseignantOut(
            id=contrat.id,
            candidature_id=contrat.candidature_id,
            etablissement_id=contrat.etablissement_id,
            syllabus=contrat.syllabus,
            date_fin=contrat.date_fin,
            statut=contrat.statut,
            signature_horodatage=contrat.signature_horodatage,
            signature_image_lulufiles_id=contrat.signature_image_lulufiles_id,
            enseignant_nom=nom,
            enseignant_prenom=prenom,
        )
        for contrat, nom, prenom in lignes
    ]


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
    reponses_formulaire: str | None = Form(None),
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
    if (
        db.query(Candidature)
        .filter(Candidature.poste_id == poste_id, Candidature.enseignant_id == enseignant.id)
        .first()
        is not None
    ):
        raise api_error(status.HTTP_409_CONFLICT, "deja_candidat", "Vous avez deja postule a ce poste.")
    if len(fichiers) > MAX_DOCUMENTS_CANDIDATURE:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "trop_de_documents", "Trop de documents joints.")

    criteres_par_type = {c.type_document: c for c in poste.criteres}
    if len(types) != len(fichiers) or set(types) != set(criteres_par_type.keys()):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "documents_incomplets",
            "Les documents fournis ne correspondent pas exactement aux criteres du poste.",
        )
    # UC-48/63 : reponses au schema_formulaire du poste, distinct des documents notes par
    # l'IA ci-dessus (deux mecanismes complementaires, voir cahier des charges).
    reponses_validees = valider_reponses_formulaire(poste.schema_formulaire, reponses_formulaire)

    candidature = Candidature(
        poste_id=poste_id,
        enseignant_id=enseignant.id,
        reponses_formulaire=reponses_validees,
        statut=StatutCandidature.EN_EVALUATION,
    )
    db.add(candidature)
    db.flush()

    # Lecture bornee de TOUS les fichiers avant la moindre ecriture chez LuluFiles : un
    # fichier refuse (taille/type) ne laisse ainsi aucun document orphelin stocke.
    contenus = [lire_upload_borne(f, MAX_DOCUMENT_CANDIDATURE_OCTETS, TYPES_DOCUMENT) for f in fichiers]
    contenu_casier = lire_upload_borne(casier_judiciaire, MAX_DOCUMENT_CANDIDATURE_OCTETS, TYPES_DOCUMENT)

    documents_a_noter = []
    for type_document, fichier, contenu in zip(types, fichiers, contenus):
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

    db.add(
        VerificationCasierJudiciaire(
            candidature_id=candidature.id,
            contenu_chiffre=chiffrer_bytes(contenu_casier),
            nom_fichier=(casier_judiciaire.filename or f"{candidature.id}.pdf")[:255],
            statut=StatutVerificationCasier.EN_ATTENTE,
            date_suppression_prevue=datetime.now(timezone.utc) + timedelta(days=CASIER_JUDICIAIRE_RETENTION_JOURS),
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
            except Exception:
                # Jamais un document bloque EN_ATTENTE pour toujours : il bascule en
                # revision manuelle, comme un echec FreeLLM ordinaire.
                logger.exception("notation IA inattendue en echec (document %s)", item["document_id"])
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

    if any(d.statut != StatutDocument.NOTE or d.note_ia is None for d in documents):
        return  # en attente (notation en cours ou revision manuelle, voir noter-manuellement)

    # Score toujours calcule, meme en cas de rejet : une contestation acceptee doit pouvoir
    # deboucher sur un contrat (creer_contrat exige un score).
    poids_total = sum(criteres_par_type[d.type_document].coefficient for d in documents) or 1.0
    candidature.score = (
        sum(d.note_ia * criteres_par_type[d.type_document].coefficient for d in documents) / poids_total
    )
    sous_seuil = any(d.note_ia < criteres_par_type[d.type_document].seuil_minimal for d in documents)
    if sous_seuil and candidature.statut == StatutCandidature.EN_EVALUATION:
        candidature.statut = StatutCandidature.REJETEE
        candidature.rejetee_le = datetime.now(timezone.utc)


@router.get("/candidatures/en-attente-revision", response_model=list[CandidatureOut])
def lister_candidatures_en_attente_revision(
    db: Session = Depends(get_db), admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL))
) -> list[Candidature]:
    """Ecran de revision manuelle (recrutement) : candidatures ayant au moins un
    document que FreeLLM n'a pas pu noter, scopees aux etablissements administres."""
    lien = db.get(AdminEtablissement, admin.id)
    if lien is None and admin.role != RoleUtilisateur.ADMIN_MINISTERIEL:
        return []
    # Sous-requete IN plutot que DISTINCT : PostgreSQL ne sait pas comparer une colonne
    # `json` (reponses_formulaire), un SELECT DISTINCT sur Candidature echouait donc
    # systematiquement - et avec lui tout l'ecran Recrutement de l'A+.
    candidatures_en_echec = select(DocumentCandidature.candidature_id).where(
        DocumentCandidature.statut == StatutDocument.ECHEC_NOTATION
    )
    requete = db.query(Candidature).join(Poste, Poste.id == Candidature.poste_id).filter(
        Candidature.id.in_(candidatures_en_echec)
    )
    # L'A++ (sans rattachement) voit la file nationale ; l'A+ celle de son etablissement.
    if admin.role != RoleUtilisateur.ADMIN_MINISTERIEL:
        requete = requete.filter(Poste.etablissement_id == lien.etablissement_id)
    return requete.all()


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
    candidature_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> Candidature:
    candidature = db.get(Candidature, candidature_id)
    if candidature is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Candidature introuvable.")

    # Bug reel corrige (audit securite, 2026-09-26) : les deux `if` ci-dessous ne
    # couvraient explicitement que ENSEIGNANT/ADMIN_ETABLISSEMENT, sans `else` - un
    # TUTEUR ou un ELEVE (qui ne correspond a aucun des deux) traversait donc les deux
    # conditions sans jamais etre bloque et repartait avec la candidature de n'importe
    # quel enseignant (documents/notes IA inclus). Seuls ENSEIGNANT (le candidat),
    # ADMIN_ETABLISSEMENT (scope verifie ci-dessous) et ADMIN_MINISTERIEL (aucune
    # restriction de perimetre, meme convention que verifier_portee_etablissement)
    # ont une raison legitime de consulter cette ressource.
    if utilisateur.role not in (
        RoleUtilisateur.ENSEIGNANT,
        RoleUtilisateur.ADMIN_ETABLISSEMENT,
        RoleUtilisateur.ADMIN_MINISTERIEL,
    ):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas habilite a consulter cette candidature.")
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
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> LienFichierOut:
    """Bug reel corrige : ni le candidat ni l'A+ n'avaient jusqu'ici de moyen de
    consulter le document lui-meme (seule la note IA etait exposee) - rend l'ecran de
    revision manuelle (UC-04) et la verification d'un A+ effectivement utilisables."""
    document = db.get(DocumentCandidature, document_id)
    if document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Document introuvable.")
    candidature = db.get(Candidature, document.candidature_id)
    # Bug reel corrige (audit securite, 2026-09-26) : meme fall-through que
    # obtenir_candidature ci-dessus - sans ce garde-fou, un TUTEUR ou un ELEVE
    # recuperait le lien signe vers la piece d'identite/diplome de n'importe quel
    # candidat enseignant.
    if utilisateur.role not in (
        RoleUtilisateur.ENSEIGNANT,
        RoleUtilisateur.ADMIN_ETABLISSEMENT,
        RoleUtilisateur.ADMIN_MINISTERIEL,
    ):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas habilite a consulter ce document.")
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


def _verification_casier_du_recruteur(
    db: Session, admin: Utilisateur, candidature_id: str
) -> tuple[Candidature, VerificationCasierJudiciaire]:
    """Art. 395/402 : lecture reservee a l'administration de l'etablissement recruteur
    (ADMIN_ETABLISSEMENT, portee verifiee) - jamais au Ministere, qui n'a aucune raison
    d'acceder aux donnees penales d'un candidat."""
    candidature = db.get(Candidature, candidature_id)
    if candidature is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Candidature introuvable.")
    poste = db.get(Poste, candidature.poste_id)
    lien = db.get(AdminEtablissement, admin.id)
    if lien is None or lien.etablissement_id != poste.etablissement_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas l'etablissement recruteur.")
    verification = candidature.verification_casier
    if verification is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Aucun casier judiciaire depose.")
    return candidature, verification


@router.get("/candidatures/{candidature_id}/casier-judiciaire", response_model=VerificationCasierOut)
def obtenir_statut_casier(
    candidature_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> VerificationCasierJudiciaire:
    purger_casiers_expires(db)
    _, verification = _verification_casier_du_recruteur(db, admin, candidature_id)
    return verification


@router.get("/candidatures/{candidature_id}/casier-judiciaire/document")
def telecharger_casier(
    candidature_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> Response:
    purger_casiers_expires(db)
    _, verification = _verification_casier_du_recruteur(db, admin, candidature_id)
    if verification.contenu_chiffre is None:
        raise api_error(
            status.HTTP_410_GONE,
            "casier_purge",
            "Le document a ete supprime (verdict rendu ou delai de conservation depasse) ; seul le statut est conserve.",
        )
    try:
        contenu = dechiffrer_bytes(verification.contenu_chiffre)
    except InvalidToken as exc:
        # Chiffre avec une autre cle (rotation de CASIER_JUDICIAIRE_ENCRYPTION_KEY, donnees
        # importees d'un autre environnement) : illisible, mais jamais une erreur 500.
        logger.error("casier_judiciaire: document illisible avec la cle actuelle (candidature %s)", candidature_id)
        raise api_error(
            status.HTTP_409_CONFLICT,
            "casier_illisible",
            "Ce document ne peut pas être déchiffré avec la clé actuelle : demandez au candidat de le déposer à nouveau.",
        ) from exc
    type_contenu = mimetypes.guess_type(verification.nom_fichier)[0] or "application/octet-stream"
    logger.info("casier_judiciaire: consultation de la candidature %s par %s", candidature_id, admin.id)
    return Response(
        content=contenu,
        media_type=type_contenu,
        headers={
            "Content-Disposition": 'attachment; filename="casier-judiciaire"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/candidatures/{candidature_id}/casier-judiciaire/verdict", response_model=VerificationCasierOut)
def rendre_verdict_casier(
    candidature_id: str,
    payload: VerdictCasierRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> VerificationCasierJudiciaire:
    """Le verdict purge immediatement le contenu brut : seul le statut conforme/non
    conforme est conserve durablement (Art. 395). Un casier non conforme elimine la
    candidature."""
    candidature, verification = _verification_casier_du_recruteur(db, admin, candidature_id)
    if verification.statut != StatutVerificationCasier.EN_ATTENTE:
        raise api_error(status.HTTP_409_CONFLICT, "deja_verifie", "Le verdict a deja ete rendu.")

    verification.statut = StatutVerificationCasier.CONFORME if payload.conforme else StatutVerificationCasier.NON_CONFORME
    verification.verifie_par_utilisateur_id = admin.id
    verification.date_verification = datetime.now(timezone.utc)
    verification.contenu_chiffre = None
    if not payload.conforme and candidature.statut == StatutCandidature.EN_EVALUATION:
        candidature.statut = StatutCandidature.REJETEE
        candidature.rejetee_le = datetime.now(timezone.utc)
    db.commit()
    db.refresh(verification)
    return verification


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
    if db.query(Contestation).filter(Contestation.candidature_id == candidature_id).first() is not None:
        raise api_error(status.HTTP_409_CONFLICT, "deja_contestee", "Cette candidature a deja fait l'objet d'une contestation.")
    depart = candidature.rejetee_le or candidature.created_at
    depart = depart if depart.tzinfo else depart.replace(tzinfo=timezone.utc)
    limite = _ajouter_jours_ouvres(depart, CONTESTATION_DELAI_JOURS)
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

    if contestation.statut != StatutContestation.EN_ATTENTE:
        raise api_error(status.HTTP_409_CONFLICT, "deja_tranchee", "Cette contestation a deja ete tranchee.")
    if payload.decision not in (StatutContestation.ACCEPTEE, StatutContestation.REJETEE):
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "decision_invalide", "Decision invalide.")
    if payload.decision == StatutContestation.REJETEE and not payload.motif_decision:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "motif_requis", "Un motif est requis en cas de rejet."
        )

    contestation.statut = payload.decision
    contestation.motif_decision = payload.motif_decision
    contestation.decided_at = datetime.now(timezone.utc)
    if payload.decision == StatutContestation.REJETEE:
        candidature.statut = StatutCandidature.REJETEE
        candidature.rejetee_le = candidature.rejetee_le or datetime.now(timezone.utc)

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
    if poste.statut != StatutPoste.OUVERT:
        raise api_error(status.HTTP_409_CONFLICT, "poste_pourvu", "Ce poste est deja pourvu.")
    verification = candidature.verification_casier
    if verification is None or verification.statut != StatutVerificationCasier.CONFORME:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "casier_non_verifie",
            "Le casier judiciaire du candidat doit etre verifie conforme avant tout contrat.",
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

    contenu_image = lire_upload_borne(signature_image, MAX_SIGNATURE_OCTETS, TYPES_IMAGE)
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
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> LienFichierOut:
    contrat = db.get(Contrat, contrat_id)
    if contrat is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contrat introuvable.")
    # Bug reel corrige (audit securite, 2026-09-26) : meme fall-through que
    # obtenir_candidature ci-dessus - sans ce garde-fou, un TUTEUR ou un ELEVE
    # recuperait l'image de signature de n'importe quel contrat enseignant.
    if utilisateur.role not in (
        RoleUtilisateur.ENSEIGNANT,
        RoleUtilisateur.ADMIN_ETABLISSEMENT,
        RoleUtilisateur.ADMIN_MINISTERIEL,
    ):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas habilite a consulter ce contrat.")
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
