import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.modules.cours_direct.models import ConsentementCameraLive, ParticipationLive, SessionLive, StatutSessionLive
from app.modules.cours_direct.schemas import (
    ConsentementCameraLiveOut,
    ParticipationLiveOut,
    SessionLiveCreate,
    SessionLiveDemarreeOut,
    SessionLiveOut,
)
from app.modules.etablissements.models import Classe
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.pedagogie.router import _verifier_enseignant_rattache

router = APIRouter(tags=["cours-direct"])


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


def _nouveau_token() -> str:
    """Placeholder de jeton de connexion - le fournisseur d'infra de diffusion reel
    (WebRTC/SFU) est un choix technique reporte a l'implementation (voir
    docs/contrat-api-phase2-3.md), sans impact sur ce contrat observable."""
    return str(uuid.uuid4())


@router.post("/classes/{classe_id}/sessions-live", response_model=SessionLiveOut, status_code=status.HTTP_201_CREATED)
def planifier_session_live(
    classe_id: str,
    payload: SessionLiveCreate,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> SessionLive:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    _verifier_enseignant_rattache(db, enseignant, classe.id)

    session = SessionLive(classe_id=classe_id, enseignant_id=enseignant.id, date_heure=payload.date_heure)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/classes/{classe_id}/sessions-live", response_model=list[SessionLiveOut])
def lister_sessions_live(
    classe_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(
        RoleUtilisateur.ELEVE,
        RoleUtilisateur.TUTEUR,
        RoleUtilisateur.ENSEIGNANT,
        RoleUtilisateur.ADMIN_ETABLISSEMENT,
        RoleUtilisateur.ADMIN_MINISTERIEL,
    ))
) -> list[SessionLive]:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    if utilisateur.role == RoleUtilisateur.ELEVE:
        _verifier_eleve_inscrit(db, utilisateur.id, classe_id)
    elif utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        _verifier_enseignant_rattache(db, utilisateur, classe.id)
    return db.query(SessionLive).filter(SessionLive.classe_id == classe_id).all()


@router.post("/sessions-live/{session_id}/demarrer", response_model=SessionLiveDemarreeOut)
def demarrer_session_live(
    session_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> SessionLiveDemarreeOut:
    session = db.get(SessionLive, session_id)
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    if session.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")
    if session.statut != StatutSessionLive.PLANIFIEE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette session ne peut pas etre demarree.")

    session.statut = StatutSessionLive.EN_COURS
    db.commit()
    db.refresh(session)
    return SessionLiveDemarreeOut(**SessionLiveOut.model_validate(session).model_dump(), token_connexion=_nouveau_token())


@router.post("/sessions-live/{session_id}/terminer", response_model=SessionLiveOut)
def terminer_session_live(
    session_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> SessionLive:
    session = db.get(SessionLive, session_id)
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    if session.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")
    if session.statut != StatutSessionLive.EN_COURS:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette session n'est pas en cours.")

    session.statut = StatutSessionLive.TERMINEE
    db.commit()
    db.refresh(session)
    return session


@router.post("/eleves/{eleve_utilisateur_id}/consentement-camera-live", response_model=ConsentementCameraLiveOut)
def donner_consentement_camera_live(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> ConsentementCameraLive:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None or eleve.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte.")

    consentement = (
        db.query(ConsentementCameraLive)
        .filter(ConsentementCameraLive.eleve_utilisateur_id == eleve_utilisateur_id)
        .first()
    )
    if consentement is not None:
        return consentement

    consentement = ConsentementCameraLive(eleve_utilisateur_id=eleve_utilisateur_id, tuteur_id=tuteur.id)
    db.add(consentement)
    db.commit()
    db.refresh(consentement)
    return consentement


@router.post("/sessions-live/{session_id}/rejoindre", response_model=ParticipationLiveOut)
def rejoindre_session_live(
    session_id: str, db: Session = Depends(get_db), eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> ParticipationLiveOut:
    session = db.get(SessionLive, session_id)
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    _verifier_eleve_inscrit(db, eleve_utilisateur.id, session.classe_id)
    if session.statut != StatutSessionLive.EN_COURS:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette session n'est pas en cours.")

    a_consenti = (
        db.query(ConsentementCameraLive)
        .filter(ConsentementCameraLive.eleve_utilisateur_id == eleve_utilisateur.id)
        .first()
        is not None
    )

    participation = (
        db.query(ParticipationLive)
        .filter(
            ParticipationLive.session_id == session_id,
            ParticipationLive.eleve_utilisateur_id == eleve_utilisateur.id,
        )
        .first()
    )
    if participation is None:
        participation = ParticipationLive(
            session_id=session_id, eleve_utilisateur_id=eleve_utilisateur.id, camera_autorisee=a_consenti
        )
        db.add(participation)
    else:
        participation.camera_autorisee = a_consenti
    db.commit()
    db.refresh(participation)
    return ParticipationLiveOut(
        id=participation.id,
        session_id=participation.session_id,
        eleve_utilisateur_id=participation.eleve_utilisateur_id,
        camera_autorisee=participation.camera_autorisee,
        token_connexion=_nouveau_token(),
    )
