"""El Professor, interface de conversation complete (les 4 personas : eleve, enseignant,
tuteur, famille).

Complete les endpoints historiques de router.py (toujours valables) avec ce qu'exige un
vrai chat : reponse diffusee au fil de l'eau (SSE), piece jointe (image ou PDF), aide
generale de l'eleve hors d'un cours, renommage/suppression d'une conversation et lecture
a voix haute. Les regles d'acces et le garde-fou de securite restent ceux de router.py.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import get_db, get_session_factory
from app.core.deps import api_error, get_current_active_user, require_roles
from app.core.documents import (
    TYPES_IMAGE,
    TYPES_PIECE_JOINTE,
    DocumentIllisibleError,
    extraire_texte_pdf,
    pages_pdf_en_images,
    texte_pdf_significatif,
    url_data_image,
)
from app.core.files import LuluFilesClient, get_files_client, lire_upload_borne
from app.core.llm import (
    ElProfessorError,
    FreeLLMClient,
    SyntheseVocaleError,
    consigne_eleve_cours,
    consigne_eleve_general,
    consigne_enseignant,
    consigne_famille,
    consigne_tuteur,
    construire_messages_el_professor,
    get_llm_client,
)
from app.core.rate_limit import consommer
from app.modules.etablissements.models import Classe
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.pedagogie.models import (
    AlerteElProfessor,
    MessageElProfessor,
    MessageElProfessorEnseignant,
    MessageElProfessorFamille,
    MessageElProfessorTuteur,
    OrigineAlerteElProfessor,
    RoleMessageElProfessor,
    RoleMessageElProfessorEnseignant,
    RoleMessageElProfessorFamille,
    RoleMessageElProfessorTuteur,
    SessionElProfessor,
    SessionElProfessorEnseignant,
    SessionElProfessorFamille,
    SessionElProfessorTuteur,
)
from app.modules.pedagogie.router import (
    _construire_contexte_eleve,
    _construire_contexte_eleve_pour_tuteur,
    _cours_lisible,
    _detecter_signal_alerte,
    _resoudre_etablissement_pour_alerte,
    _verifier_acces_session_famille,
    texte_du_cours,
)
from app.modules.pedagogie.schemas import (
    RenommerSessionElProfessor,
    SessionElProfessorEleveCreate,
    SessionElProfessorOut,
    SessionElProfessorResumeOut,
    SyntheseVocaleRequest,
)

router = APIRouter(tags=["el-professor"])

MAX_TAILLE_PIECE_JOINTE = 10 * 1024 * 1024
# FreeLLM agrege des offres gratuites (voir ADR-002) : sans plafond, un seul compte pourrait
# epuiser le quota journalier de toute la plateforme. Decision du 2026-09-27 : 1000 messages
# par jour et par compte (fenetre glissante de 24 h).
_MESSAGES_PAR_JOUR = 1000
_LECTURES_VOCALES_PAR_HEURE = 30

_ALERTE_ADULTE = (
    "\n\n⚠️ Cette situation semble sensible : parlez-en sans délai à l'administration de "
    "l'établissement (ou aux autorités compétentes si l'urgence l'exige). Une alerte a été "
    "préparée pour l'administration."
)
_ALERTE_ELEVE = (
    "\n\n💛 Si tu vis quelque chose de difficile, tu n'es pas seul·e : parles-en dès que possible "
    "à un adulte de confiance (un parent, un enseignant, l'administration de ton établissement). "
    "En cas de danger immédiat, va vers l'adulte le plus proche ou appelle la police. L'équipe de "
    "ton établissement a été prévenue pour pouvoir t'aider."
)

_CONSIGNE_DETRESSE_ELEVE = (
    "\n\nIMPORTANT : le dernier message de l'élève exprime peut-être une détresse ou un danger. "
    "Réponds en 4 à 6 phrases courtes, avec douceur, sans tableau ni liste : dis-lui que ce "
    "n'est pas sa faute, qu'il ou elle mérite d'être en sécurité, et encourage-le ou la à en "
    "parler aujourd'hui même à un adulte de confiance ou à l'administration de son établissement."
)


@dataclass(frozen=True)
class _Persona:
    modele_session: type
    modele_message: type
    roles: tuple[RoleUtilisateur, ...]
    origine_alerte: OrigineAlerteElProfessor


_PERSONAS = {
    "eleve": _Persona(SessionElProfessor, MessageElProfessor, (RoleUtilisateur.ELEVE,), OrigineAlerteElProfessor.ELEVE),
    "enseignant": _Persona(
        SessionElProfessorEnseignant,
        MessageElProfessorEnseignant,
        (RoleUtilisateur.ENSEIGNANT,),
        OrigineAlerteElProfessor.ENSEIGNANT,
    ),
    "tuteur": _Persona(
        SessionElProfessorTuteur, MessageElProfessorTuteur, (RoleUtilisateur.TUTEUR,), OrigineAlerteElProfessor.TUTEUR
    ),
    "famille": _Persona(
        SessionElProfessorFamille,
        MessageElProfessorFamille,
        (RoleUtilisateur.TUTEUR, RoleUtilisateur.ELEVE),
        OrigineAlerteElProfessor.FAMILLE,
    ),
}


def _session_accessible(db: Session, persona: str, session_id: str, utilisateur: Utilisateur, *, gestion: bool = False):
    """Session de l'appelant pour cette persona, sinon 404 (on ne revele jamais l'existence
    d'une conversation d'autrui). `gestion` : renommer/supprimer - dans un fil familial,
    reserve au tuteur qui l'a ouvert (le supprimer effacerait aussi l'historique de l'enfant)."""
    definition = _PERSONAS.get(persona)
    if definition is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Conversation introuvable.")
    if utilisateur.role not in definition.roles:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Accès non autorisé.")
    session = db.get(definition.modele_session, session_id)
    if persona == "famille":
        session = _verifier_acces_session_famille(session, utilisateur)
        if gestion and utilisateur.role != RoleUtilisateur.TUTEUR:
            raise api_error(
                status.HTTP_403_FORBIDDEN, "acces_refuse", "Seul le tuteur peut renommer ou supprimer ce fil familial."
            )
        return session
    proprietaire = {
        "eleve": lambda s: s.eleve_utilisateur_id,
        "enseignant": lambda s: s.enseignant_id,
        "tuteur": lambda s: s.tuteur_id,
    }[persona]
    if session is None or proprietaire(session) != utilisateur.id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Conversation introuvable.")
    return session


def _niveau_eleve(db: Session, eleve_utilisateur_id: str) -> str | None:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
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
    return classe.niveau if classe else None


@dataclass
class _Fil:
    consigne: str
    role_utilisateur: object
    qui_parle: str | None
    message_alerte: str
    # Cote eleve, seul son propre message est analyse : la reponse d'El Professor a une
    # question d'histoire ou de SVT contient trop souvent un mot-cle ("violence", "abus"...).
    analyser_reponse: bool


def _preparer_fil(
    db: Session, persona: str, session, utilisateur: Utilisateur, files_client: LuluFilesClient
) -> _Fil:
    if persona == "eleve":
        if session.cours_id is not None:
            cours = _cours_lisible(db, utilisateur, session.cours_id)
            descriptif = {"titre": cours.titre, "chapitre": cours.chapitre, "format": cours.format.value}
            consigne = consigne_eleve_cours(descriptif, texte_du_cours(db, cours, files_client))
        else:
            consigne = consigne_eleve_general(_niveau_eleve(db, utilisateur.id))
        return _Fil(consigne, RoleMessageElProfessor.ELEVE, None, _ALERTE_ELEVE, analyser_reponse=False)
    if persona == "enseignant":
        contexte = (
            _construire_contexte_eleve(db, utilisateur.id, session.eleve_utilisateur_id)
            if session.eleve_utilisateur_id
            else None
        )
        return _Fil(consigne_enseignant(contexte), RoleMessageElProfessorEnseignant.ENSEIGNANT, None, _ALERTE_ADULTE, True)
    if persona == "tuteur":
        contexte = _construire_contexte_eleve_pour_tuteur(db, session.eleve_utilisateur_id)
        return _Fil(consigne_tuteur(contexte), RoleMessageElProfessorTuteur.TUTEUR, None, _ALERTE_ADULTE, True)

    if session.rejointe_le is None:
        raise api_error(
            status.HTTP_409_CONFLICT, "session_non_rejointe", "Cette session n'a pas encore été rejointe par l'enfant."
        )
    est_tuteur = utilisateur.role == RoleUtilisateur.TUTEUR
    contexte = _construire_contexte_eleve_pour_tuteur(db, session.eleve_utilisateur_id)
    return _Fil(
        consigne_famille(contexte),
        RoleMessageElProfessorFamille.TUTEUR if est_tuteur else RoleMessageElProfessorFamille.ELEVE,
        "tuteur" if est_tuteur else "eleve",
        _ALERTE_ADULTE,
        True,
    )


def _preparer_piece_jointe(fichier: UploadFile | None) -> tuple[dict, list[str]]:
    """Retourne les colonnes piece_jointe_* a enregistrer et les images a montrer au modele
    vision pour cette seule question. Un PDF est lu ici (FreeLLM ignorerait le fichier) :
    son texte, ou ses premieres pages en images s'il est scanne."""
    if fichier is None or not fichier.filename:
        return {}, []
    contenu = lire_upload_borne(fichier, MAX_TAILLE_PIECE_JOINTE, TYPES_PIECE_JOINTE)
    type_contenu = (fichier.content_type or "").split(";")[0].strip().lower()
    colonnes = {"piece_jointe_nom": fichier.filename[:255], "piece_jointe_type": type_contenu}
    if type_contenu in TYPES_IMAGE:
        return colonnes, [url_data_image(contenu, type_contenu)]
    try:
        texte = extraire_texte_pdf(contenu)
        if texte_pdf_significatif(texte):
            return {**colonnes, "piece_jointe_texte": texte}, []
        images = [url_data_image(page, "image/png") for page in pages_pdf_en_images(contenu)]
    except DocumentIllisibleError as exc:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "document_illisible",
            "Ce PDF est illisible ou protégé par un mot de passe.",
        ) from exc
    return colonnes, images


def _historique(session) -> list[dict]:
    return [
        {
            "role": m.role.value,
            "contenu": m.contenu,
            "piece_jointe_nom": m.piece_jointe_nom,
            "piece_jointe_type": m.piece_jointe_type,
            "piece_jointe_texte": m.piece_jointe_texte,
        }
        for m in session.messages
    ]


def _message_out(message) -> dict:
    return {
        "id": message.id,
        "session_id": message.session_id,
        "role": message.role.value,
        "contenu": message.contenu,
        "piece_jointe_nom": message.piece_jointe_nom,
        "piece_jointe_type": message.piece_jointe_type,
        "created_at": message.created_at.isoformat(),
    }


def _evenement(nom: str, donnees: dict) -> str:
    return f"event: {nom}\ndata: {json.dumps(donnees, ensure_ascii=False)}\n\n"


@router.post("/el-professor/{persona}/sessions/{session_id}/flux")
def poser_question_en_flux(
    persona: str,
    session_id: str,
    question: str = Form(..., min_length=1),
    fichier: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> StreamingResponse:
    """Evenements SSE : `delta` ({texte}) au fil de la reponse, puis `fin` (les deux
    messages enregistres) ou `erreur` ({message}). Rien n'est enregistre si la reponse
    echoue : l'utilisateur peut simplement renvoyer sa question."""
    session = _session_accessible(db, persona, session_id, utilisateur)
    consommer(
        db,
        f"el_professor:{utilisateur.id}",
        _MESSAGES_PAR_JOUR,
        86400,
        f"Vous avez atteint la limite de {_MESSAGES_PAR_JOUR} messages par jour avec El Professor. "
        "Reessayez demain.",
    )
    fil = _preparer_fil(db, persona, session, utilisateur, files_client)
    piece_jointe, images = _preparer_piece_jointe(fichier)
    messages = construire_messages_el_professor(
        fil.consigne,
        _historique(session),
        question,
        qui_parle=fil.qui_parle,
        piece_jointe=piece_jointe,
        images=images,
    )
    definition = _PERSONAS[persona]
    eleve_concerne = getattr(session, "eleve_utilisateur_id", None)
    etablissement_alerte = _resoudre_etablissement_pour_alerte(db, eleve_concerne)
    signal_question = _detecter_signal_alerte(question)
    if signal_question and persona == "eleve":
        # Verification reelle : sans ce rappel cible, le modele repondait a un enfant en
        # detresse par un long tableau de demarches. Le signal est connu avant l'appel.
        messages[0]["content"] += _CONSIGNE_DETRESSE_ELEVE
    pose_le = datetime.now(timezone.utc)

    def generer() -> Iterator[str]:
        # Premier octet immediat : les proxys (Render, Vercel) gardent la connexion ouverte
        # meme quand le modele vision met une vingtaine de secondes a commencer.
        yield _evenement("debut", {})
        morceaux: list[str] = []
        try:
            for morceau in llm_client.diffuser_el_professor(messages):
                morceaux.append(morceau)
                yield _evenement("delta", {"texte": morceau})
        except ElProfessorError:
            yield _evenement("erreur", {"message": "El Professor n'a pas pu répondre, veuillez réessayer."})
            return
        reponse = "".join(morceaux).strip()
        if not reponse:
            yield _evenement("erreur", {"message": "El Professor n'a pas pu répondre, veuillez réessayer."})
            return

        alerte = signal_question or (fil.analyser_reponse and _detecter_signal_alerte(reponse))
        if alerte:
            reponse += fil.message_alerte
            yield _evenement("delta", {"texte": fil.message_alerte})

        with session_factory() as ecriture:
            message_utilisateur = definition.modele_message(
                session_id=session_id, role=fil.role_utilisateur, contenu=question, created_at=pose_le, **piece_jointe
            )
            message_assistant = definition.modele_message(
                session_id=session_id, role=type(fil.role_utilisateur)("assistant"), contenu=reponse
            )
            ecriture.add_all([message_utilisateur, message_assistant])
            if alerte:
                ecriture.add(
                    AlerteElProfessor(
                        origine=definition.origine_alerte,
                        session_id=session_id,
                        etablissement_id=etablissement_alerte,
                        eleve_utilisateur_id=eleve_concerne,
                        motif=question[:1000],
                    )
                )
            ecriture.commit()
            fin = {
                "message_utilisateur": _message_out(message_utilisateur),
                "message_assistant": _message_out(message_assistant),
            }
        yield _evenement("fin", fin)

    return StreamingResponse(
        generer(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.patch("/el-professor/{persona}/sessions/{session_id}", response_model=SessionElProfessorResumeOut)
def renommer_session(
    persona: str,
    session_id: str,
    payload: RenommerSessionElProfessor,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> SessionElProfessorResumeOut:
    session = _session_accessible(db, persona, session_id, utilisateur, gestion=True)
    session.sujet = payload.sujet.strip()
    db.commit()
    return SessionElProfessorResumeOut(id=session.id, sujet=session.sujet)


@router.delete("/el-professor/{persona}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_session(
    persona: str,
    session_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> Response:
    """Les alertes deja emises sont conservees (elles ne pointent pas la session par cle
    etrangere) : supprimer une conversation n'efface jamais un signalement."""
    session = _session_accessible(db, persona, session_id, utilisateur, gestion=True)
    modele_message = _PERSONAS[persona].modele_message
    db.query(modele_message).filter(modele_message.session_id == session.id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/el-professor/eleve/sessions", response_model=list[SessionElProfessorOut])
def lister_mes_sessions_eleve(
    db: Session = Depends(get_db),
    eleve: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> list[SessionElProfessor]:
    return (
        db.query(SessionElProfessor)
        .filter(SessionElProfessor.eleve_utilisateur_id == eleve.id)
        .order_by(SessionElProfessor.created_at.desc())
        .all()
    )


@router.post("/el-professor/eleve/sessions", response_model=SessionElProfessorOut, status_code=status.HTTP_201_CREATED)
def ouvrir_session_eleve(
    payload: SessionElProfessorEleveCreate,
    db: Session = Depends(get_db),
    eleve: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> SessionElProfessor:
    if payload.cours_id is not None:
        _cours_lisible(db, eleve, payload.cours_id)
        existante = (
            db.query(SessionElProfessor)
            .filter(SessionElProfessor.eleve_utilisateur_id == eleve.id, SessionElProfessor.cours_id == payload.cours_id)
            .first()
        )
        if existante is not None:
            return existante
    session = SessionElProfessor(
        eleve_utilisateur_id=eleve.id, cours_id=payload.cours_id, sujet=(payload.sujet or "").strip() or None
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/el-professor/synthese-vocale")
def lire_a_voix_haute(
    payload: SyntheseVocaleRequest,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.TUTEUR)
    ),
) -> Response:
    consommer(db, f"el_professor_voix:{utilisateur.id}", _LECTURES_VOCALES_PAR_HEURE, 3600)
    try:
        audio = llm_client.synthese_vocale(payload.texte)
    except SyntheseVocaleError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "synthese_echouee", "La lecture à voix haute est indisponible pour le moment."
        ) from exc
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "private, max-age=3600"})
