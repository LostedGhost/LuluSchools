from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, get_current_user, require_roles
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.core.llm import FreeLLMClient, QuizGenerationError, get_llm_client
from app.modules.etablissements.models import Classe
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.pedagogie.models import Cours, FormatCours, QuestionQuiz, Quiz, TentativeQuiz
from app.modules.pedagogie.schemas import (
    CoursOut,
    QuizCreate,
    QuizOut,
    TentativeQuizCreate,
    TentativeQuizOut,
)
from app.modules.recrutement.models import Contrat, StatutContrat

MAX_TAILLE_COURS_OCTETS = 50 * 1024 * 1024

router = APIRouter(tags=["pedagogie"])


def _verifier_enseignant_rattache(db: Session, enseignant: Utilisateur, etablissement_id: str) -> None:
    if enseignant.role != RoleUtilisateur.ENSEIGNANT:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action.")
    contrat = (
        db.query(Contrat)
        .filter(
            Contrat.enseignant_id == enseignant.id,
            Contrat.etablissement_id == etablissement_id,
            Contrat.statut == StatutContrat.SIGNE,
        )
        .first()
    )
    if contrat is None:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas rattache a cet etablissement."
        )


def _verifier_eleve_inscrit(db: Session, eleve_utilisateur_id: str, classe_id: str) -> Eleve:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Compte eleve introuvable.")
    inscription = (
        db.query(Inscription)
        .filter(
            Inscription.eleve_id == eleve.id,
            Inscription.classe_id == classe_id,
            Inscription.statut == StatutInscription.VALIDEE,
        )
        .first()
    )
    if inscription is None:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas inscrit dans cette classe.")
    return eleve


@router.post("/classes/{classe_id}/cours", response_model=CoursOut, status_code=status.HTTP_201_CREATED)
def publier_cours(
    classe_id: str,
    titre: str = Form(...),
    chapitre: str = Form(...),
    format: FormatCours = Form(...),
    contenu_texte: str | None = Form(None),
    fichier: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    enseignant: Utilisateur = Depends(get_current_active_user),
) -> Cours:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    _verifier_enseignant_rattache(db, enseignant, classe.etablissement_id)

    lulufiles_file_id = None
    if fichier is not None:
        contenu = fichier.file.read()
        if len(contenu) > MAX_TAILLE_COURS_OCTETS:
            raise api_error(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "fichier_trop_volumineux", "Fichier limite a 50 Mo."
            )
        try:
            lulufiles_file_id = files_client.upload(
                contenu, fichier.filename or titre, fichier.content_type or "application/octet-stream"
            )
        except FileStorageError as exc:
            raise api_error(
                status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible de stocker le fichier, veuillez reessayer."
            ) from exc

    cours = Cours(
        classe_id=classe_id,
        enseignant_id=enseignant.id,
        titre=titre,
        chapitre=chapitre,
        format=format,
        contenu_texte=contenu_texte,
        lulufiles_file_id=lulufiles_file_id,
    )
    db.add(cours)
    db.commit()
    db.refresh(cours)
    return cours


@router.get("/classes/{classe_id}/cours", response_model=list[CoursOut])
def lister_cours(
    classe_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_user)
) -> list[Cours]:
    if utilisateur.role == RoleUtilisateur.ELEVE:
        _verifier_eleve_inscrit(db, utilisateur.id, classe_id)
    return db.query(Cours).filter(Cours.classe_id == classe_id).all()


@router.post("/cours/{cours_id}/quiz", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
def creer_quiz(
    cours_id: str,
    payload: QuizCreate,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    enseignant: Utilisateur = Depends(get_current_active_user),
) -> Quiz:
    """UC-07 : les questions sont generees par le LLM a partir du contenu texte du cours."""
    cours = db.get(Cours, cours_id)
    if cours is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Cours introuvable.")
    if cours.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce cours ne vous appartient pas.")
    if not cours.contenu_texte:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "contenu_texte_requis",
            "Le cours doit avoir un contenu_texte pour generer un quiz.",
        )

    try:
        questions_generees = llm_client.generer_quiz(cours.contenu_texte, payload.nombre_questions)
    except QuizGenerationError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "generation_echouee", "Impossible de generer le quiz, veuillez reessayer."
        ) from exc

    quiz = Quiz(cours_id=cours_id, seuil_reussite=payload.seuil_reussite)
    db.add(quiz)
    db.flush()
    for ordre, question in enumerate(questions_generees):
        db.add(
            QuestionQuiz(
                quiz_id=quiz.id,
                ordre=ordre,
                enonce=question["enonce"],
                choix=question["choix"],
                reponse_correcte_index=question["reponse_correcte_index"],
            )
        )
    db.commit()
    db.refresh(quiz)
    return quiz


@router.get("/quiz/{quiz_id}", response_model=QuizOut)
def obtenir_quiz(
    quiz_id: str, db: Session = Depends(get_db), eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> Quiz:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Quiz introuvable.")
    cours = db.get(Cours, quiz.cours_id)
    _verifier_eleve_inscrit(db, eleve_utilisateur.id, cours.classe_id)
    return quiz


@router.post("/quiz/{quiz_id}/tentatives", response_model=TentativeQuizOut, status_code=status.HTTP_201_CREATED)
def tenter_quiz(
    quiz_id: str,
    payload: TentativeQuizCreate,
    db: Session = Depends(get_db),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> TentativeQuiz:
    """Tentatives illimitees (UC-07)."""
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Quiz introuvable.")
    cours = db.get(Cours, quiz.cours_id)
    eleve = _verifier_eleve_inscrit(db, eleve_utilisateur.id, cours.classe_id)

    questions = sorted(quiz.questions, key=lambda q: q.ordre)
    if len(payload.reponses) != len(questions):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "reponses_incompletes",
            f"Attendu {len(questions)} reponses, recu {len(payload.reponses)}.",
        )

    bonnes_reponses = sum(
        1 for question, reponse in zip(questions, payload.reponses) if reponse == question.reponse_correcte_index
    )
    score = (bonnes_reponses / len(questions)) * 100 if questions else 0.0

    tentative = TentativeQuiz(
        quiz_id=quiz_id,
        eleve_id=eleve.id,
        reponses=payload.reponses,
        score=score,
        reussie=score >= quiz.seuil_reussite,
    )
    db.add(tentative)
    db.commit()
    db.refresh(tentative)
    return tentative
