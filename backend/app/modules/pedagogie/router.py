from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, get_current_user, require_roles
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.core.llm import ElProfessorError, FreeLLMClient, QuizGenerationError, get_llm_client
from app.modules.etablissements.models import AffectationEnseignant, Classe
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.pedagogie.models import (
    Cours,
    FormatCours,
    MessageElProfessor,
    QuestionQuiz,
    Quiz,
    RoleMessageElProfessor,
    SessionElProfessor,
    TentativeQuiz,
)
from app.modules.pedagogie.schemas import (
    CoursOut,
    LienFichierOut,
    QuestionElProfessorCreate,
    QuizCreate,
    QuizOut,
    SessionElProfessorOut,
    TentativeQuizCreate,
    TentativeQuizOut,
)

MAX_TAILLE_COURS_OCTETS = 50 * 1024 * 1024
MAX_TAILLE_COURS_VIDEO_OCTETS = 200 * 1024 * 1024  # UC-15 (Phase 3), delegue - la duree (15 min) n'est pas
# verifiable cote serveur sans bibliotheque de parsing video, limitation assumee pour ce premier jet.

router = APIRouter(tags=["pedagogie"])


def _verifier_enseignant_rattache(db: Session, enseignant: Utilisateur, classe_id: str) -> None:
    """Verifie que l'enseignant a bien une AFFECTATION sur cette classe precise (pas
    seulement un contrat signe avec l'etablissement - voir AffectationEnseignant pour
    le contexte du changement)."""
    if enseignant.role != RoleUtilisateur.ENSEIGNANT:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action.")
    affectation = (
        db.query(AffectationEnseignant)
        .filter(
            AffectationEnseignant.enseignant_id == enseignant.id,
            AffectationEnseignant.classe_id == classe_id,
        )
        .first()
    )
    if affectation is None:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette classe ne vous est pas affectee."
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
    _verifier_enseignant_rattache(db, enseignant, classe.id)

    lulufiles_file_id = None
    if fichier is not None:
        contenu = fichier.file.read()
        limite = MAX_TAILLE_COURS_VIDEO_OCTETS if format == FormatCours.VIDEO else MAX_TAILLE_COURS_OCTETS
        if len(contenu) > limite:
            raise api_error(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "fichier_trop_volumineux",
                f"Fichier limite a {limite // (1024 * 1024)} Mo.",
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


@router.get("/cours/{cours_id}/lien-fichier", response_model=LienFichierOut)
def obtenir_lien_fichier_cours(
    cours_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> LienFichierOut:
    """Bug reel corrige : `Cours.lulufiles_file_id` etait stocke a l'upload (UC-06) mais
    jamais transforme en lien consultable - un cours pdf/audio/video n'avait aucun moyen
    d'etre effectivement lu par un eleve. Meme controle d'acces que lister_cours."""
    cours = db.get(Cours, cours_id)
    if cours is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Cours introuvable.")
    if utilisateur.role == RoleUtilisateur.ELEVE:
        _verifier_eleve_inscrit(db, utilisateur.id, cours.classe_id)
    elif utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        _verifier_enseignant_rattache(db, utilisateur, cours.classe_id)
    if not cours.lulufiles_file_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ce cours n'a pas de fichier associe.")

    try:
        url = files_client.get_signed_link(cours.lulufiles_file_id, disposition="inline")
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible d'obtenir le lien du fichier, veuillez reessayer."
        ) from exc
    return LienFichierOut(url=url)


@router.get("/cours/{cours_id}/quiz", response_model=list[QuizOut])
def lister_quiz(
    cours_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_user)
) -> list[Quiz]:
    cours = db.get(Cours, cours_id)
    if cours is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Cours introuvable.")
    if utilisateur.role == RoleUtilisateur.ELEVE:
        _verifier_eleve_inscrit(db, utilisateur.id, cours.classe_id)
    return db.query(Quiz).filter(Quiz.cours_id == cours_id).all()


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
            status.HTTP_422_UNPROCESSABLE_ENTITY,
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
            status.HTTP_422_UNPROCESSABLE_ENTITY,
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


@router.get("/quiz/{quiz_id}/mes-tentatives", response_model=list[TentativeQuizOut])
def lister_mes_tentatives(
    quiz_id: str, db: Session = Depends(get_db), eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> list[TentativeQuiz]:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Quiz introuvable.")
    cours = db.get(Cours, quiz.cours_id)
    eleve = _verifier_eleve_inscrit(db, eleve_utilisateur.id, cours.classe_id)
    return (
        db.query(TentativeQuiz)
        .filter(TentativeQuiz.quiz_id == quiz_id, TentativeQuiz.eleve_id == eleve.id)
        .order_by(TentativeQuiz.created_at.desc())
        .all()
    )


@router.post(
    "/cours/{cours_id}/el-professor/session", response_model=SessionElProfessorOut, status_code=status.HTTP_201_CREATED
)
def ouvrir_session_el_professor(
    cours_id: str,
    db: Session = Depends(get_db),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> SessionElProfessor:
    """UC-14 : upsert, une seule session par (eleve, cours)."""
    cours = db.get(Cours, cours_id)
    if cours is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Cours introuvable.")
    _verifier_eleve_inscrit(db, eleve_utilisateur.id, cours.classe_id)

    session = (
        db.query(SessionElProfessor)
        .filter(
            SessionElProfessor.eleve_utilisateur_id == eleve_utilisateur.id,
            SessionElProfessor.cours_id == cours_id,
        )
        .first()
    )
    if session is not None:
        return session

    session = SessionElProfessor(eleve_utilisateur_id=eleve_utilisateur.id, cours_id=cours_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/cours/{cours_id}/el-professor/session", response_model=SessionElProfessorOut)
def obtenir_session_el_professor(
    cours_id: str,
    db: Session = Depends(get_db),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> SessionElProfessor:
    session = (
        db.query(SessionElProfessor)
        .filter(
            SessionElProfessor.eleve_utilisateur_id == eleve_utilisateur.id,
            SessionElProfessor.cours_id == cours_id,
        )
        .first()
    )
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Aucune session El Professor pour ce cours.")
    return session


@router.post(
    "/el-professor/sessions/{session_id}/messages",
    response_model=SessionElProfessorOut,
    status_code=status.HTTP_201_CREATED,
)
def poser_question_el_professor(
    session_id: str,
    payload: QuestionElProfessorCreate,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> SessionElProfessor:
    session = db.get(SessionElProfessor, session_id)
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    if session.eleve_utilisateur_id != eleve_utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")
    cours = db.get(Cours, session.cours_id)

    historique = [{"role": m.role.value, "contenu": m.contenu} for m in session.messages]
    try:
        reponse = llm_client.repondre_question_el_professor(cours.contenu_texte or "", historique, payload.question)
    except ElProfessorError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "reponse_echouee", "Impossible d'obtenir une reponse, veuillez reessayer."
        ) from exc

    db.add(MessageElProfessor(session_id=session_id, role=RoleMessageElProfessor.ELEVE, contenu=payload.question))
    db.add(MessageElProfessor(session_id=session_id, role=RoleMessageElProfessor.ASSISTANT, contenu=reponse))
    db.commit()
    db.refresh(session)
    return session
