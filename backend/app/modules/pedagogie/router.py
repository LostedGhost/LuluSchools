import unicodedata
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import journaliser_action_ministerielle
from app.core.database import get_db
from app.core.deps import (
    api_error,
    get_current_active_user,
    get_current_user,
    require_roles,
    verifier_portee_etablissement,
)
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.core.llm import ElProfessorError, FreeLLMClient, QuizGenerationError, get_llm_client
from app.modules.etablissements.models import AffectationEnseignant, Classe, Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.pedagogie.models import (
    AlerteElProfessor,
    Cours,
    FormatCours,
    MessageElProfessor,
    MessageElProfessorEnseignant,
    MessageElProfessorFamille,
    MessageElProfessorTuteur,
    OrigineAlerteElProfessor,
    QuestionQuiz,
    Quiz,
    RoleMessageElProfessor,
    RoleMessageElProfessorEnseignant,
    RoleMessageElProfessorFamille,
    RoleMessageElProfessorTuteur,
    SessionElProfessor,
    SessionElProfessorEnseignant,
    SessionElProfessorFamille,
    SessionElProfessorTuteur,
    TentativeQuiz,
)
from app.modules.pedagogie.schemas import (
    AdminCoursOut,
    AdminCoursPageOut,
    AlerteElProfessorOut,
    CoursOut,
    LienFichierOut,
    MasquerContenuRequest,
    QuestionElProfessorCreate,
    QuizCreate,
    QuizOut,
    SessionElProfessorEnseignantCreate,
    SessionElProfessorEnseignantOut,
    SessionElProfessorFamilleCreate,
    SessionElProfessorFamilleOut,
    SessionElProfessorOut,
    SessionElProfessorTuteurCreate,
    SessionElProfessorTuteurOut,
    TentativeQuizCreate,
    TentativeQuizOut,
)
from app.modules.vie_scolaire.models import EntreeVieScolaire

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
    requete = db.query(Cours).filter(Cours.classe_id == classe_id)
    if utilisateur.role == RoleUtilisateur.ELEVE:
        _verifier_eleve_inscrit(db, utilisateur.id, classe_id)
        # UC-37/53 (lot admin ministeriel) : un cours masque par le Ministere reste visible
        # a l'enseignant/A+/A++ (pour savoir ce qui a ete masque), jamais a l'eleve.
        requete = requete.filter(Cours.masque_par_id.is_(None))
    return requete.all()


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


def _cours_vers_admin_out(
    cours: Cours, etablissement_id: str, etablissement_nom: str, enseignant: Utilisateur
) -> AdminCoursOut:
    return AdminCoursOut(
        id=cours.id,
        titre=cours.titre,
        chapitre=cours.chapitre,
        format=cours.format,
        classe_id=cours.classe_id,
        etablissement_id=etablissement_id,
        etablissement_nom=etablissement_nom,
        enseignant_id=cours.enseignant_id,
        enseignant_nom=enseignant.nom,
        enseignant_prenom=enseignant.prenom,
        masque=cours.masque_par_id is not None,
        created_at=cours.created_at,
    )


@router.get("/admin/cours", response_model=AdminCoursPageOut)
def lister_cours_supervision(
    etablissement_id: str | None = None,
    enseignant_id: str | None = None,
    masque: bool | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> AdminCoursPageOut:
    """UC-37/53 : supervision transverse - aucun endpoint existant ne permettait de voir
    les cours de plusieurs etablissements a la fois (seul GET /classes/{id}/cours existe,
    par classe). Pagination serveur obligatoire (meme regle que l'annuaire etablissements,
    ADR-009) : le volume grandit avec le nombre d'etablissements/classes/enseignants."""
    limit = max(1, min(limit, 60))
    offset = max(0, offset)

    requete = db.query(Cours).join(Classe, Cours.classe_id == Classe.id)
    if etablissement_id:
        requete = requete.filter(Classe.etablissement_id == etablissement_id)
    if enseignant_id:
        requete = requete.filter(Cours.enseignant_id == enseignant_id)
    if masque is not None:
        requete = requete.filter(Cours.masque_par_id.isnot(None) if masque else Cours.masque_par_id.is_(None))

    total = requete.with_entities(func.count(Cours.id)).scalar() or 0
    page = requete.order_by(Cours.created_at.desc()).offset(offset).limit(limit).all()

    classe_par_id = {
        c.id: c for c in db.query(Classe).filter(Classe.id.in_({cours.classe_id for cours in page}))
    } if page else {}
    etablissement_ids = {c.etablissement_id for c in classe_par_id.values()}
    etablissements = {
        e.id: e.nom for e in db.query(Etablissement).filter(Etablissement.id.in_(etablissement_ids)).all()
    } if etablissement_ids else {}
    enseignant_ids = {c.enseignant_id for c in page}
    enseignants = {
        u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_(enseignant_ids)).all()
    } if enseignant_ids else {}

    items = [
        _cours_vers_admin_out(
            cours,
            classe_par_id[cours.classe_id].etablissement_id,
            etablissements.get(classe_par_id[cours.classe_id].etablissement_id, ""),
            enseignants[cours.enseignant_id],
        )
        for cours in page
    ]
    return AdminCoursPageOut(items=items, total=total, limit=limit, offset=offset)


@router.post("/cours/{cours_id}/masquer", response_model=CoursOut)
def masquer_cours(
    cours_id: str,
    payload: MasquerContenuRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Cours:
    """UC-37/53 : masquage non destructif (meme pattern que Message.masque_par en
    messagerie, Phase 2/3) - le cours reste en base et visible a l'enseignant/A+/A++,
    seul l'eleve ne le voit plus (voir lister_cours)."""
    cours = db.get(Cours, cours_id)
    if cours is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Cours introuvable.")
    if cours.masque_par_id is not None:
        raise api_error(status.HTTP_409_CONFLICT, "deja_masque", "Ce cours est deja masque.")

    cours.masque_par_id = admin.id
    cours.masque_le = datetime.now(timezone.utc)
    journaliser_action_ministerielle(db, admin, "cours.masquer", "cours", cours.id, payload.motif)
    db.commit()
    db.refresh(cours)
    return cours


@router.post("/cours/{cours_id}/demasquer", response_model=CoursOut)
def demasquer_cours(
    cours_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Cours:
    cours = db.get(Cours, cours_id)
    if cours is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Cours introuvable.")
    if cours.masque_par_id is None:
        raise api_error(status.HTTP_409_CONFLICT, "pas_masque", "Ce cours n'est pas masque.")

    cours.masque_par_id = None
    cours.masque_le = None
    journaliser_action_ministerielle(db, admin, "cours.demasquer", "cours", cours.id, None)
    db.commit()
    db.refresh(cours)
    return cours


# --- UC-27 : El Professor, volet enseignant (conseil educatif/moral/professionnel) ---

_MOTS_CLES_ALERTE = (
    "maltraitance", "violence", "abus", "viol", "suicide", "se tuer", "se faire du mal",
    "automutilation", "scarification", "en danger", "urgence", "menace", "frappe", "battu",
    "battue", "harcelement sexuel", "attouchement", "abandon",
)


def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.combining(c))


def _detecter_signal_alerte(texte: str) -> bool:
    """UC-27.3 : garde-fou de securite - heuristique volontairement simple (mots-cles) et
    permissive (mieux vaut un faux positif occasionnel qu'un vrai signal manque). Ne
    remplace jamais un jugement humain, se contente de forcer une recommandation
    d'escalade explicite et de preparer une alerte pour l'administration."""
    normalise = _sans_accents(texte.lower())
    return any(mot in normalise for mot in _MOTS_CLES_ALERTE)


def _classes_communes(db: Session, enseignant_id: str, eleve: Eleve) -> list[AffectationEnseignant]:
    classes_eleve = {
        i.classe_id
        for i in db.query(Inscription).filter(
            Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE
        )
    }
    if not classes_eleve:
        return []
    return (
        db.query(AffectationEnseignant)
        .filter(AffectationEnseignant.enseignant_id == enseignant_id, AffectationEnseignant.classe_id.in_(classes_eleve))
        .all()
    )


def _construire_contexte_eleve(db: Session, enseignant_id: str, eleve_utilisateur_id: str) -> str | None:
    """Ne donne a El Professor QUE ce que l'enseignant a lui-meme le droit de voir (meme
    portee que vie_scolaire/router.py : tout pour le professeur principal, seulement ses
    propres entrees pour un enseignant de matiere) - jamais plus."""
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        return None
    affectations = _classes_communes(db, enseignant_id, eleve)
    if not affectations:
        return None

    entrees: list[EntreeVieScolaire] = []
    for affectation in affectations:
        requete = db.query(EntreeVieScolaire).filter(
            EntreeVieScolaire.classe_id == affectation.classe_id, EntreeVieScolaire.eleve_id == eleve.id
        )
        if not affectation.est_professeur_principal:
            requete = requete.filter(EntreeVieScolaire.auteur_id == enseignant_id)
        entrees.extend(requete.all())
    if not entrees:
        return None

    lignes = [
        f"- [{e.nature.value}]" + (f" ({e.matiere})" if e.matiere else "") + f" {e.date_survenue.isoformat()} : {e.description}"
        for e in sorted(entrees, key=lambda e: e.date_survenue)
    ]
    return "\n".join(lignes)


def _resoudre_etablissement_pour_alerte(db: Session, eleve_utilisateur_id: str | None) -> str | None:
    if eleve_utilisateur_id is None:
        return None
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        return None
    inscription = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .first()
    )
    if inscription is None:
        return None
    classe = db.get(Classe, inscription.classe_id)
    return classe.etablissement_id if classe else None


@router.post(
    "/el-professor-enseignant/sessions",
    response_model=SessionElProfessorEnseignantOut,
    status_code=status.HTTP_201_CREATED,
)
def ouvrir_session_el_professor_enseignant(
    payload: SessionElProfessorEnseignantCreate,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> SessionElProfessorEnseignant:
    if payload.eleve_utilisateur_id is not None:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == payload.eleve_utilisateur_id).first()
        if eleve is None or not _classes_communes(db, enseignant.id, eleve):
            raise api_error(
                status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est dans aucune de vos classes."
            )

    session = SessionElProfessorEnseignant(
        enseignant_id=enseignant.id, eleve_utilisateur_id=payload.eleve_utilisateur_id, sujet=payload.sujet
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/el-professor-enseignant/sessions", response_model=list[SessionElProfessorEnseignantOut])
def lister_mes_sessions_el_professor_enseignant(
    db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> list[SessionElProfessorEnseignant]:
    return (
        db.query(SessionElProfessorEnseignant)
        .filter(SessionElProfessorEnseignant.enseignant_id == enseignant.id)
        .order_by(SessionElProfessorEnseignant.created_at.desc())
        .all()
    )


@router.get("/el-professor-enseignant/sessions/{session_id}", response_model=SessionElProfessorEnseignantOut)
def obtenir_session_el_professor_enseignant(
    session_id: str,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> SessionElProfessorEnseignant:
    session = db.get(SessionElProfessorEnseignant, session_id)
    if session is None or session.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    return session


@router.post(
    "/el-professor-enseignant/sessions/{session_id}/messages",
    response_model=SessionElProfessorEnseignantOut,
    status_code=status.HTTP_201_CREATED,
)
def poser_question_el_professor_enseignant(
    session_id: str,
    payload: QuestionElProfessorCreate,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> SessionElProfessorEnseignant:
    session = db.get(SessionElProfessorEnseignant, session_id)
    if session is None or session.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")

    contexte_eleve = (
        _construire_contexte_eleve(db, enseignant.id, session.eleve_utilisateur_id)
        if session.eleve_utilisateur_id
        else None
    )
    historique = [{"role": m.role.value, "contenu": m.contenu} for m in session.messages]
    try:
        reponse = llm_client.conseiller_enseignant(contexte_eleve, historique, payload.question)
    except ElProfessorError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "reponse_echouee", "Impossible d'obtenir une reponse, veuillez reessayer."
        ) from exc

    if _detecter_signal_alerte(payload.question) or _detecter_signal_alerte(reponse):
        reponse = (
            f"{reponse}\n\n⚠️ Cette situation semble sensible : parlez-en sans delai a "
            "l'administration de votre etablissement (ou aux autorites competentes si "
            "l'urgence l'exige). Une alerte a ete preparee pour l'administration."
        )
        db.add(
            AlerteElProfessor(
                origine=OrigineAlerteElProfessor.ENSEIGNANT,
                session_id=session.id,
                etablissement_id=_resoudre_etablissement_pour_alerte(db, session.eleve_utilisateur_id),
                eleve_utilisateur_id=session.eleve_utilisateur_id,
                motif=payload.question[:1000],
            )
        )

    db.add(
        MessageElProfessorEnseignant(
            session_id=session_id, role=RoleMessageElProfessorEnseignant.ENSEIGNANT, contenu=payload.question
        )
    )
    db.add(
        MessageElProfessorEnseignant(
            session_id=session_id, role=RoleMessageElProfessorEnseignant.ASSISTANT, contenu=reponse
        )
    )
    db.commit()
    db.refresh(session)
    return session


@router.get("/etablissements/{etablissement_id}/alertes-el-professor", response_model=list[AlerteElProfessorOut])
def lister_alertes_el_professor(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[AlerteElProfessor]:
    verifier_portee_etablissement(db, admin, etablissement_id)
    return (
        db.query(AlerteElProfessor)
        .filter(AlerteElProfessor.etablissement_id == etablissement_id)
        .order_by(AlerteElProfessor.created_at.desc())
        .all()
    )


@router.post("/alertes-el-professor/{alerte_id}/traiter", response_model=AlerteElProfessorOut)
def traiter_alerte_el_professor(
    alerte_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> AlerteElProfessor:
    alerte = db.get(AlerteElProfessor, alerte_id)
    if alerte is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Alerte introuvable.")
    if alerte.etablissement_id is None:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette alerte n'est rattachee a aucun etablissement.")
    verifier_portee_etablissement(db, admin, alerte.etablissement_id)

    alerte.traite = True
    alerte.traite_par_id = admin.id
    db.commit()
    db.refresh(alerte)
    return alerte


# --- UC-32 : El Professor, volet tuteur ---


def _verifier_tuteur_de_l_eleve(db: Session, tuteur_id: str, eleve_utilisateur_id: str) -> Eleve:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None or eleve.tuteur_id != tuteur_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte.")
    return eleve


def _construire_contexte_eleve_pour_tuteur(db: Session, eleve_utilisateur_id: str) -> str | None:
    """Contrairement a l'enseignant (dont la portee vie_scolaire est parfois filtree a
    ses propres entrees, voir _construire_contexte_eleve), le tuteur a deja acces a
    TOUTE la vie scolaire de son enfant (vie_scolaire/router.py) - le contexte fourni a
    El Professor reprend donc l'integralite, sans filtre supplementaire."""
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        return None
    entrees = db.query(EntreeVieScolaire).filter(EntreeVieScolaire.eleve_id == eleve.id).all()
    if not entrees:
        return None
    lignes = [
        f"- [{e.nature.value}]" + (f" ({e.matiere})" if e.matiere else "") + f" {e.date_survenue.isoformat()} : {e.description}"
        for e in sorted(entrees, key=lambda e: e.date_survenue)
    ]
    return "\n".join(lignes)


@router.post(
    "/el-professor-tuteur/sessions",
    response_model=SessionElProfessorTuteurOut,
    status_code=status.HTTP_201_CREATED,
)
def ouvrir_session_el_professor_tuteur(
    payload: SessionElProfessorTuteurCreate,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> SessionElProfessorTuteur:
    _verifier_tuteur_de_l_eleve(db, tuteur.id, payload.eleve_utilisateur_id)

    session = SessionElProfessorTuteur(
        tuteur_id=tuteur.id, eleve_utilisateur_id=payload.eleve_utilisateur_id, sujet=payload.sujet
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/el-professor-tuteur/sessions", response_model=list[SessionElProfessorTuteurOut])
def lister_mes_sessions_el_professor_tuteur(
    db: Session = Depends(get_db), tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR))
) -> list[SessionElProfessorTuteur]:
    return (
        db.query(SessionElProfessorTuteur)
        .filter(SessionElProfessorTuteur.tuteur_id == tuteur.id)
        .order_by(SessionElProfessorTuteur.created_at.desc())
        .all()
    )


@router.get("/el-professor-tuteur/sessions/{session_id}", response_model=SessionElProfessorTuteurOut)
def obtenir_session_el_professor_tuteur(
    session_id: str,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> SessionElProfessorTuteur:
    session = db.get(SessionElProfessorTuteur, session_id)
    if session is None or session.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    return session


@router.post(
    "/el-professor-tuteur/sessions/{session_id}/messages",
    response_model=SessionElProfessorTuteurOut,
    status_code=status.HTTP_201_CREATED,
)
def poser_question_el_professor_tuteur(
    session_id: str,
    payload: QuestionElProfessorCreate,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> SessionElProfessorTuteur:
    session = db.get(SessionElProfessorTuteur, session_id)
    if session is None or session.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")

    contexte_eleve = _construire_contexte_eleve_pour_tuteur(db, session.eleve_utilisateur_id)
    historique = [{"role": m.role.value, "contenu": m.contenu} for m in session.messages]
    try:
        reponse = llm_client.conseiller_tuteur(contexte_eleve, historique, payload.question)
    except ElProfessorError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "reponse_echouee", "Impossible d'obtenir une reponse, veuillez reessayer."
        ) from exc

    if _detecter_signal_alerte(payload.question) or _detecter_signal_alerte(reponse):
        reponse = (
            f"{reponse}\n\n⚠️ Cette situation semble sensible : parlez-en sans delai a "
            "l'administration de l'etablissement de votre enfant (ou aux autorites "
            "competentes si l'urgence l'exige). Une alerte a ete preparee pour l'administration."
        )
        db.add(
            AlerteElProfessor(
                origine=OrigineAlerteElProfessor.TUTEUR,
                session_id=session.id,
                etablissement_id=_resoudre_etablissement_pour_alerte(db, session.eleve_utilisateur_id),
                eleve_utilisateur_id=session.eleve_utilisateur_id,
                motif=payload.question[:1000],
            )
        )

    db.add(
        MessageElProfessorTuteur(session_id=session_id, role=RoleMessageElProfessorTuteur.TUTEUR, contenu=payload.question)
    )
    db.add(
        MessageElProfessorTuteur(session_id=session_id, role=RoleMessageElProfessorTuteur.ASSISTANT, contenu=reponse)
    )
    db.commit()
    db.refresh(session)
    return session


@router.get("/mes-enfants/{eleve_utilisateur_id}/alertes-el-professor", response_model=list[AlerteElProfessorOut])
def lister_alertes_el_professor_de_mon_enfant(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> list[AlerteElProfessor]:
    """UC-32.2 : un tuteur voit les alertes concernant SON enfant (qu'elles viennent
    d'une session enseignant ou d'une session tuteur), jamais celles d'un autre eleve.
    UC-37.2 : les alertes d'origine FAMILLE sont exclues ici - le tuteur peut etre la
    source du danger detecte dans un fil familial, elles n'escaladent donc JAMAIS vers
    lui, uniquement vers l'administration (voir lister_alertes_el_professor)."""
    _verifier_tuteur_de_l_eleve(db, tuteur.id, eleve_utilisateur_id)
    return (
        db.query(AlerteElProfessor)
        .filter(
            AlerteElProfessor.eleve_utilisateur_id == eleve_utilisateur_id,
            AlerteElProfessor.origine != OrigineAlerteElProfessor.FAMILLE,
        )
        .order_by(AlerteElProfessor.created_at.desc())
        .all()
    )


# --- UC-37 : El Professor Famille (fil partage tuteur + enfant) ---


@router.post(
    "/el-professor-famille/sessions",
    response_model=SessionElProfessorFamilleOut,
    status_code=status.HTTP_201_CREATED,
)
def ouvrir_session_el_professor_famille(
    payload: SessionElProfessorFamilleCreate,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> SessionElProfessorFamille:
    """UC-37.1 : toujours cree par le tuteur, qui "invite" ainsi son enfant - la session
    reste inutilisable (aucun message des deux cotes) tant que l'enfant ne l'a pas
    explicitement rejointe (voir rejoindre_session_el_professor_famille, R3)."""
    _verifier_tuteur_de_l_eleve(db, tuteur.id, payload.eleve_utilisateur_id)

    session = SessionElProfessorFamille(
        tuteur_id=tuteur.id, eleve_utilisateur_id=payload.eleve_utilisateur_id, sujet=payload.sujet
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _verifier_acces_session_famille(session: SessionElProfessorFamille | None, utilisateur: Utilisateur) -> SessionElProfessorFamille:
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    if utilisateur.role == RoleUtilisateur.TUTEUR and session.tuteur_id == utilisateur.id:
        return session
    if utilisateur.role == RoleUtilisateur.ELEVE and session.eleve_utilisateur_id == utilisateur.id:
        return session
    raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")


@router.get("/el-professor-famille/sessions", response_model=list[SessionElProfessorFamilleOut])
def lister_mes_sessions_el_professor_famille(
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR, RoleUtilisateur.ELEVE)),
) -> list[SessionElProfessorFamille]:
    if utilisateur.role == RoleUtilisateur.TUTEUR:
        filtre = SessionElProfessorFamille.tuteur_id == utilisateur.id
    else:
        filtre = SessionElProfessorFamille.eleve_utilisateur_id == utilisateur.id
    return (
        db.query(SessionElProfessorFamille).filter(filtre).order_by(SessionElProfessorFamille.created_at.desc()).all()
    )


@router.get("/el-professor-famille/sessions/{session_id}", response_model=SessionElProfessorFamilleOut)
def obtenir_session_el_professor_famille(
    session_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR, RoleUtilisateur.ELEVE)),
) -> SessionElProfessorFamille:
    session = db.get(SessionElProfessorFamille, session_id)
    return _verifier_acces_session_famille(session, utilisateur)


@router.post("/el-professor-famille/sessions/{session_id}/rejoindre", response_model=SessionElProfessorFamilleOut)
def rejoindre_session_el_professor_famille(
    session_id: str,
    db: Session = Depends(get_db),
    eleve: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> SessionElProfessorFamille:
    """UC-37.1 : l'invitation du tuteur ne suffit pas - l'enfant doit explicitement
    accepter de rejoindre le fil familial avant que quiconque puisse y ecrire (R3)."""
    session = db.get(SessionElProfessorFamille, session_id)
    if session is None or session.eleve_utilisateur_id != eleve.id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    if session.rejointe_le is None:
        session.rejointe_le = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
    return session


@router.post(
    "/el-professor-famille/sessions/{session_id}/messages",
    response_model=SessionElProfessorFamilleOut,
    status_code=status.HTTP_201_CREATED,
)
def poser_question_el_professor_famille(
    session_id: str,
    payload: QuestionElProfessorCreate,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR, RoleUtilisateur.ELEVE)),
) -> SessionElProfessorFamille:
    session = db.get(SessionElProfessorFamille, session_id)
    session = _verifier_acces_session_famille(session, utilisateur)
    if session.rejointe_le is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "session_non_rejointe",
            "Cette session n'a pas encore ete rejointe par l'enfant.",
        )

    qui_parle = "tuteur" if utilisateur.role == RoleUtilisateur.TUTEUR else "eleve"
    role_message = (
        RoleMessageElProfessorFamille.TUTEUR
        if utilisateur.role == RoleUtilisateur.TUTEUR
        else RoleMessageElProfessorFamille.ELEVE
    )
    contexte_eleve = _construire_contexte_eleve_pour_tuteur(db, session.eleve_utilisateur_id)
    historique = [{"role": m.role.value, "contenu": m.contenu} for m in session.messages]
    try:
        reponse = llm_client.conseiller_famille(contexte_eleve, historique, payload.question, qui_parle)
    except ElProfessorError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "reponse_echouee", "Impossible d'obtenir une reponse, veuillez reessayer."
        ) from exc

    if _detecter_signal_alerte(payload.question) or _detecter_signal_alerte(reponse):
        reponse = (
            f"{reponse}\n\n⚠️ Cette situation semble sensible : parlez-en sans delai a "
            "l'administration de l'etablissement (ou aux autorites competentes si "
            "l'urgence l'exige). Une alerte a ete preparee pour l'administration."
        )
        db.add(
            AlerteElProfessor(
                origine=OrigineAlerteElProfessor.FAMILLE,
                session_id=session.id,
                etablissement_id=_resoudre_etablissement_pour_alerte(db, session.eleve_utilisateur_id),
                eleve_utilisateur_id=session.eleve_utilisateur_id,
                motif=payload.question[:1000],
            )
        )

    db.add(MessageElProfessorFamille(session_id=session_id, role=role_message, contenu=payload.question))
    db.add(
        MessageElProfessorFamille(session_id=session_id, role=RoleMessageElProfessorFamille.ASSISTANT, contenu=reponse)
    )
    db.commit()
    db.refresh(session)
    return session
