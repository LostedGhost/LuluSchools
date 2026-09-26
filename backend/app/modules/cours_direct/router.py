import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, require_roles
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.core.llm import FreeLLMClient, ResumeSessionLiveError, get_llm_client
from app.core.security import decode_token
from app.modules.cours_direct.models import (
    CaptureTableauSession,
    ConsentementCameraLive,
    DemandeCraie,
    MessageSessionLive,
    ModePermissionEcriture,
    PanneauTableau,
    ParticipationLive,
    PermissionEcritureTableau,
    ResumeSessionLive,
    SessionLive,
    StatutDemandeCraie,
    StatutSessionLive,
    TraitTableau,
    TypeTraitTableau,
)
from app.modules.cours_direct.realtime import gestionnaire_live
from app.modules.cours_direct.rendu_tableau import rendre_panneau_png
from app.modules.cours_direct.schemas import (
    CaptureTableauOut,
    ConsentementCameraLiveOut,
    DemandeCraieOut,
    EtatTableauOut,
    MessageSessionLiveCreate,
    MessageSessionLiveOut,
    PanneauAvecTraitsOut,
    PanneauTableauOut,
    ParticipationLiveOut,
    PermissionEcritureCreate,
    PermissionEcritureOut,
    ResumeSessionLiveOut,
    SessionLiveCreate,
    SessionLiveDemarreeOut,
    SessionLiveOut,
    TraitTableauCreate,
    TraitTableauOut,
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


def _verifier_tuteur_a_un_enfant_dans_la_classe(db: Session, tuteur_id: str, classe_id: str) -> None:
    """UC-29.2 : lister_sessions_live acceptait TUTEUR dans son require_roles sans
    jamais verifier la portee reelle pour ce role (contrairement a ELEVE/ENSEIGNANT
    juste en dessous) - un tuteur authentifie pouvait lister les sessions de N'IMPORTE
    QUELLE classe. Corrige : au moins un de ses enfants doit y etre valide."""
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
    elif utilisateur.role == RoleUtilisateur.TUTEUR:
        _verifier_tuteur_a_un_enfant_dans_la_classe(db, utilisateur.id, classe_id)
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
    session_id: str,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> SessionLive:
    session = db.get(SessionLive, session_id)
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    if session.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")
    if session.statut != StatutSessionLive.EN_COURS:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette session n'est pas en cours.")

    session.statut = StatutSessionLive.TERMINEE
    _capturer_tous_les_panneaux(db, session_id, files_client)
    _generer_resume_session_live(db, session_id, llm_client)
    db.commit()
    db.refresh(session)
    return session


def _generer_resume_session_live(db: Session, session_id: str, llm_client: FreeLLMClient) -> None:
    """UC-33.1 : resume texte factuel a la cloture, a partir du chat + du contenu
    textuel du tableau (les blocs TEXTE uniquement - un trait libre n'a pas de
    representation textuelle exploitable). Best-effort comme _capturer_tous_les_panneaux :
    un echec FreeLLM ne bloque jamais la cloture, deja actee."""
    messages = (
        db.query(MessageSessionLive)
        .filter(MessageSessionLive.session_id == session_id)
        .order_by(MessageSessionLive.created_at.asc())
        .all()
    )
    panneaux = db.query(PanneauTableau).filter(PanneauTableau.session_id == session_id).all()
    textes_tableau = []
    for panneau in panneaux:
        traits_texte = (
            db.query(TraitTableau)
            .filter(TraitTableau.panneau_id == panneau.id, TraitTableau.type == TypeTraitTableau.TEXTE)
            .all()
        )
        textes_tableau.extend(t.donnees.get("texte", "") for t in traits_texte if t.donnees.get("texte"))

    if not messages and not textes_tableau:
        return

    try:
        contenu = llm_client.resumer_session_live(
            [m.contenu for m in messages], "\n".join(textes_tableau)
        )
    except ResumeSessionLiveError:
        return

    db.add(ResumeSessionLive(session_id=session_id, contenu=contenu))


@router.get("/sessions-live/{session_id}/resume", response_model=ResumeSessionLiveOut)
def obtenir_resume_session_live(
    session_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> ResumeSessionLive:
    """UC-33.1/33.2 : observation asynchrone - le tuteur ne rejoint jamais la session en
    direct, il consulte ce resume une fois la session terminee et cloturee."""
    a_un_enfant_participant = (
        db.query(ParticipationLive)
        .join(Eleve, Eleve.utilisateur_id == ParticipationLive.eleve_utilisateur_id)
        .filter(ParticipationLive.session_id == session_id, Eleve.tuteur_id == utilisateur.id)
        .first()
        is not None
    )
    if not a_un_enfant_participant:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "acces_refuse", "Aucun de vos enfants n'a participe a cette session."
        )
    resume = db.query(ResumeSessionLive).filter(ResumeSessionLive.session_id == session_id).first()
    if resume is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "introuvable", "Aucun resume n'est disponible pour cette session."
        )
    return resume


def _capturer_tous_les_panneaux(db: Session, session_id: str, files_client: LuluFilesClient) -> None:
    """UC-25.6 : a la cloture, chaque panneau ayant au moins un trait est fige en PNG
    (voir rendu_tableau.py) - echec de stockage tolere (ne bloque jamais la cloture de la
    session, deja actee) plutot que remonte comme une erreur a l'enseignant."""
    panneaux = db.query(PanneauTableau).filter(PanneauTableau.session_id == session_id).all()
    for panneau in panneaux:
        traits = db.query(TraitTableau).filter(TraitTableau.panneau_id == panneau.id).all()
        if not traits:
            continue
        try:
            png = rendre_panneau_png(traits)
            file_id = files_client.upload(png, f"tableau-{panneau.id}.png", "image/png")
        except FileStorageError:
            continue
        db.add(CaptureTableauSession(session_id=session_id, panneau_id=panneau.id, lulufiles_file_id=file_id))


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
    # UC-25.5 : la "salle sociale" pre-cours - un eleve peut rejoindre et discuter avec
    # ses camarades AVANT l'arrivee du professeur (PLANIFIEE), pas seulement une fois la
    # session EN_COURS. Le tableau reste verrouille en ecriture (voir _a_le_droit_ecrire)
    # et le chat est journalise comme le reste (voir MessageSessionLive).
    if session.statut not in (StatutSessionLive.PLANIFIEE, StatutSessionLive.EN_COURS):
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette session est deja terminee.")

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


# --- UC-25 : tableau collaboratif, permissions de craie, chat de session ---


def _est_organisateur(session: SessionLive, utilisateur: Utilisateur) -> bool:
    return utilisateur.role == RoleUtilisateur.ENSEIGNANT and session.enseignant_id == utilisateur.id


def _est_participant(db: Session, session_id: str, utilisateur: Utilisateur) -> bool:
    if utilisateur.role == RoleUtilisateur.ELEVE:
        return (
            db.query(ParticipationLive)
            .filter(
                ParticipationLive.session_id == session_id,
                ParticipationLive.eleve_utilisateur_id == utilisateur.id,
            )
            .first()
            is not None
        )
    return False


def _verifier_session_et_acces(db: Session, session_id: str, utilisateur: Utilisateur) -> SessionLive:
    session = db.get(SessionLive, session_id)
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    if not _est_organisateur(session, utilisateur) and not _est_participant(db, session_id, utilisateur):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous ne participez pas a cette session.")
    return session


def _a_le_droit_ecrire(db: Session, session_id: str, utilisateur: Utilisateur, session: SessionLive) -> bool:
    if _est_organisateur(session, utilisateur):
        return True
    return (
        db.query(PermissionEcritureTableau)
        .filter(
            PermissionEcritureTableau.session_id == session_id,
            PermissionEcritureTableau.eleve_utilisateur_id == utilisateur.id,
        )
        .first()
        is not None
    )


def _premier_panneau(db: Session, session_id: str) -> PanneauTableau:
    panneau = (
        db.query(PanneauTableau)
        .filter(PanneauTableau.session_id == session_id)
        .order_by(PanneauTableau.ordre.asc())
        .first()
    )
    if panneau is not None:
        return panneau
    panneau = PanneauTableau(session_id=session_id, ordre=0)
    db.add(panneau)
    db.commit()
    db.refresh(panneau)
    return panneau


@router.get("/sessions-live/{session_id}/tableau", response_model=EtatTableauOut)
def obtenir_etat_tableau(
    session_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> EtatTableauOut:
    session = _verifier_session_et_acces(db, session_id, utilisateur)
    _premier_panneau(db, session_id)  # garantit au moins un panneau des le premier acces

    panneaux = (
        db.query(PanneauTableau).filter(PanneauTableau.session_id == session_id).order_by(PanneauTableau.ordre.asc()).all()
    )
    panneaux_out = []
    for panneau in panneaux:
        traits = (
            db.query(TraitTableau)
            .filter(TraitTableau.panneau_id == panneau.id)
            .order_by(TraitTableau.created_at.asc())
            .all()
        )
        panneaux_out.append(PanneauAvecTraitsOut(panneau=panneau, traits=traits))

    permissions = db.query(PermissionEcritureTableau).filter(PermissionEcritureTableau.session_id == session_id).all()
    demandes = (
        db.query(DemandeCraie)
        .filter(DemandeCraie.session_id == session_id, DemandeCraie.statut == StatutDemandeCraie.EN_ATTENTE)
        .all()
        if _est_organisateur(session, utilisateur)
        else []
    )
    return EtatTableauOut(panneaux=panneaux_out, permissions=permissions, demandes_en_attente=demandes)


@router.post(
    "/sessions-live/{session_id}/tableau/panneaux", response_model=PanneauTableauOut, status_code=status.HTTP_201_CREATED
)
def ajouter_panneau_tableau(
    session_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> PanneauTableau:
    session = db.get(SessionLive, session_id)
    if session is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Session introuvable.")
    if not _est_organisateur(session, enseignant):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")

    dernier_ordre = (
        db.query(PanneauTableau)
        .filter(PanneauTableau.session_id == session_id)
        .order_by(PanneauTableau.ordre.desc())
        .first()
    )
    panneau = PanneauTableau(session_id=session_id, ordre=(dernier_ordre.ordre + 1) if dernier_ordre else 0)
    db.add(panneau)
    db.commit()
    db.refresh(panneau)
    return panneau


async def _ajouter_trait(
    db: Session, session_id: str, panneau_id: str, utilisateur: Utilisateur, payload: TraitTableauCreate
) -> TraitTableau:
    session = _verifier_session_et_acces(db, session_id, utilisateur)
    panneau = db.get(PanneauTableau, panneau_id)
    if panneau is None or panneau.session_id != session_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Panneau introuvable.")
    if not _a_le_droit_ecrire(db, session_id, utilisateur, session):
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "ecriture_non_autorisee",
            "Vous n'avez pas (ou plus) la craie sur ce tableau.",
        )

    trait = TraitTableau(panneau_id=panneau_id, auteur_id=utilisateur.id, type=payload.type, donnees=payload.donnees)
    db.add(trait)
    db.commit()
    db.refresh(trait)
    await gestionnaire_live.diffuser(
        session_id, {"type": "trait", "panneau_id": panneau_id, "trait": TraitTableauOut.model_validate(trait).model_dump(mode="json")}
    )
    return trait


@router.post(
    "/sessions-live/{session_id}/tableau/panneaux/{panneau_id}/traits",
    response_model=TraitTableauOut,
    status_code=status.HTTP_201_CREATED,
)
async def ajouter_trait_tableau(
    session_id: str,
    panneau_id: str,
    payload: TraitTableauCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> TraitTableau:
    return await _ajouter_trait(db, session_id, panneau_id, utilisateur, payload)


@router.post(
    "/sessions-live/{session_id}/tableau/panneaux/{panneau_id}/effacer",
    response_model=TraitTableauOut,
    status_code=status.HTTP_201_CREATED,
)
async def effacer_panneau_tableau(
    session_id: str,
    panneau_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> TraitTableau:
    """Le 'chiffon' - efface tout ce qui precede sur ce panneau (voir
    rendu_tableau.rendre_panneau_png pour comment cet evenement est rejoue). Accessible a
    qui detient la craie, pas seulement au professeur (§3.1 du cahier des charges : le
    chiffon accompagne la craie)."""
    return await _ajouter_trait(db, session_id, panneau_id, utilisateur, TraitTableauCreate(type=TypeTraitTableau.EFFACEMENT))


@router.post("/sessions-live/{session_id}/demande-craie", response_model=DemandeCraieOut, status_code=status.HTTP_201_CREATED)
async def demander_la_craie(
    session_id: str, db: Session = Depends(get_db), eleve: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> DemandeCraie:
    session = _verifier_session_et_acces(db, session_id, eleve)
    if _a_le_droit_ecrire(db, session_id, eleve, session):
        raise api_error(status.HTTP_409_CONFLICT, "deja_autorise", "Vous avez deja la craie sur ce tableau.")

    existante = (
        db.query(DemandeCraie)
        .filter(
            DemandeCraie.session_id == session_id,
            DemandeCraie.eleve_utilisateur_id == eleve.id,
            DemandeCraie.statut == StatutDemandeCraie.EN_ATTENTE,
        )
        .first()
    )
    if existante is not None:
        return existante

    demande = DemandeCraie(session_id=session_id, eleve_utilisateur_id=eleve.id)
    db.add(demande)
    db.commit()
    db.refresh(demande)
    await gestionnaire_live.diffuser(
        session_id, {"type": "demande_craie", "demande": DemandeCraieOut.model_validate(demande).model_dump(mode="json")}
    )
    return demande


@router.get("/sessions-live/{session_id}/demandes-craie", response_model=list[DemandeCraieOut])
def lister_demandes_craie(
    session_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> list[DemandeCraie]:
    session = db.get(SessionLive, session_id)
    if session is None or not _est_organisateur(session, enseignant):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")
    return (
        db.query(DemandeCraie)
        .filter(DemandeCraie.session_id == session_id, DemandeCraie.statut == StatutDemandeCraie.EN_ATTENTE)
        .all()
    )


async def _trancher_demande_craie(
    db: Session, session_id: str, demande_id: str, enseignant: Utilisateur, accordee: bool
) -> DemandeCraie:
    session = db.get(SessionLive, session_id)
    if session is None or not _est_organisateur(session, enseignant):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")
    demande = db.get(DemandeCraie, demande_id)
    if demande is None or demande.session_id != session_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Demande introuvable.")
    if demande.statut != StatutDemandeCraie.EN_ATTENTE:
        raise api_error(status.HTTP_409_CONFLICT, "deja_traitee", "Cette demande a deja ete traitee.")

    demande.statut = StatutDemandeCraie.ACCORDEE if accordee else StatutDemandeCraie.REFUSEE
    if accordee:
        _accorder_permission(db, session_id, demande.eleve_utilisateur_id, enseignant.id, ModePermissionEcriture.ACCORDEE)
    db.commit()
    db.refresh(demande)
    await gestionnaire_live.diffuser(
        session_id,
        {
            "type": "demande_craie_tranchee",
            "demande": DemandeCraieOut.model_validate(demande).model_dump(mode="json"),
        },
    )
    return demande


@router.post("/sessions-live/{session_id}/demandes-craie/{demande_id}/accorder", response_model=DemandeCraieOut)
async def accorder_demande_craie(
    session_id: str, demande_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> DemandeCraie:
    return await _trancher_demande_craie(db, session_id, demande_id, enseignant, accordee=True)


@router.post("/sessions-live/{session_id}/demandes-craie/{demande_id}/refuser", response_model=DemandeCraieOut)
async def refuser_demande_craie(
    session_id: str, demande_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> DemandeCraie:
    return await _trancher_demande_craie(db, session_id, demande_id, enseignant, accordee=False)


def _accorder_permission(
    db: Session, session_id: str, eleve_utilisateur_id: str, accordee_par_id: str, mode: ModePermissionEcriture
) -> PermissionEcritureTableau:
    permission = (
        db.query(PermissionEcritureTableau)
        .filter(
            PermissionEcritureTableau.session_id == session_id,
            PermissionEcritureTableau.eleve_utilisateur_id == eleve_utilisateur_id,
        )
        .first()
    )
    if permission is not None:
        permission.mode = mode
        permission.accordee_par_id = accordee_par_id
    else:
        permission = PermissionEcritureTableau(
            session_id=session_id, eleve_utilisateur_id=eleve_utilisateur_id, mode=mode, accordee_par_id=accordee_par_id
        )
        db.add(permission)
    db.flush()
    return permission


@router.post(
    "/sessions-live/{session_id}/permissions-ecriture",
    response_model=PermissionEcritureOut,
    status_code=status.HTTP_201_CREATED,
)
async def preter_la_craie(
    session_id: str,
    payload: PermissionEcritureCreate,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> PermissionEcritureTableau:
    """"Craie pretee" - accordee directement par le professeur, sans demande prealable de
    l'eleve (par opposition a la "craie accordee" suite a une DemandeCraie)."""
    session = db.get(SessionLive, session_id)
    if session is None or not _est_organisateur(session, enseignant):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")
    _verifier_eleve_inscrit(db, payload.eleve_utilisateur_id, session.classe_id)

    permission = _accorder_permission(
        db, session_id, payload.eleve_utilisateur_id, enseignant.id, ModePermissionEcriture.PRETEE
    )
    db.commit()
    db.refresh(permission)
    await gestionnaire_live.diffuser(
        session_id, {"type": "permission_accordee", "eleve_utilisateur_id": payload.eleve_utilisateur_id}
    )
    return permission


@router.delete("/sessions-live/{session_id}/permissions-ecriture/{eleve_utilisateur_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoquer_la_craie(
    session_id: str,
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> None:
    """Retrait possible a tout instant, y compris en plein trait (§3.1) - le prochain
    envoi de trait de l'eleve sera simplement refuse (403), aucun etat de 'trait en
    cours' n'est modelise cote serveur."""
    session = db.get(SessionLive, session_id)
    if session is None or not _est_organisateur(session, enseignant):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette session ne vous appartient pas.")
    permission = (
        db.query(PermissionEcritureTableau)
        .filter(
            PermissionEcritureTableau.session_id == session_id,
            PermissionEcritureTableau.eleve_utilisateur_id == eleve_utilisateur_id,
        )
        .first()
    )
    if permission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Aucune permission d'ecriture pour cet eleve.")
    db.delete(permission)
    db.commit()
    await gestionnaire_live.diffuser(session_id, {"type": "permission_revoquee", "eleve_utilisateur_id": eleve_utilisateur_id})


@router.get("/sessions-live/{session_id}/captures", response_model=list[CaptureTableauOut])
def lister_captures_tableau(
    session_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> list[CaptureTableauSession]:
    _verifier_session_et_acces(db, session_id, utilisateur)
    return db.query(CaptureTableauSession).filter(CaptureTableauSession.session_id == session_id).all()


@router.post(
    "/sessions-live/{session_id}/messages", response_model=MessageSessionLiveOut, status_code=status.HTTP_201_CREATED
)
async def envoyer_message_session_live(
    session_id: str,
    payload: MessageSessionLiveCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> MessageSessionLive:
    """UC-25.5 : chat de la session (salle sociale pre-cours incluse) - immuable, comme
    la messagerie generale, mais circuit dedie et plus simple (voir MessageSessionLive)."""
    _verifier_session_et_acces(db, session_id, utilisateur)
    if not payload.contenu.strip():
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "contenu_vide", "Le message ne peut pas etre vide.")

    message = MessageSessionLive(session_id=session_id, auteur_id=utilisateur.id, contenu=payload.contenu.strip())
    db.add(message)
    db.commit()
    db.refresh(message)
    await gestionnaire_live.diffuser(
        session_id, {"type": "message", "message": MessageSessionLiveOut.model_validate(message).model_dump(mode="json")}
    )
    return message


@router.get("/sessions-live/{session_id}/messages", response_model=list[MessageSessionLiveOut])
def lister_messages_session_live(
    session_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> list[MessageSessionLive]:
    _verifier_session_et_acces(db, session_id, utilisateur)
    return (
        db.query(MessageSessionLive)
        .filter(MessageSessionLive.session_id == session_id)
        .order_by(MessageSessionLive.created_at.asc())
        .all()
    )


@router.websocket("/ws/sessions-live/{session_id}")
async def canal_temps_reel_session_live(
    websocket: WebSocket, session_id: str, token: str, db: Session = Depends(get_db)
) -> None:
    """Canal de diffusion temps reel (traits du tableau, permissions, chat) et de
    relais de signalisation WebRTC en maillage (mesh) entre pairs - voir cahier des
    charges §3.1/R2 : pas de SFU tiers, une signalisation maison suffit pour des effectifs
    de classe. Les MUTATIONS passent toujours par les endpoints REST ci-dessus (validees,
    journalisees) ; ce canal ne fait que les diffuser, sauf pour le relais webrtc_signal
    qui n'a rien a persister. `db` passe par Depends (pas un appel direct a get_db) pour
    que les tests puissent rediriger vers leur moteur via app.dependency_overrides, comme
    pour toute route HTTP du projet."""
    try:
        payload = decode_token(token)
        utilisateur = db.get(Utilisateur, payload.get("sub")) if payload.get("type") == "access" else None
    except Exception:
        utilisateur = None
    if utilisateur is None:
        await websocket.close(code=4401)
        return

    session = db.get(SessionLive, session_id)
    if session is None or not (
        _est_organisateur(session, utilisateur) or _est_participant(db, session_id, utilisateur)
    ):
        await websocket.close(code=4403)
        return

    await gestionnaire_live.connecter(session_id, websocket, utilisateur.id)
    try:
        while True:
            evenement = await websocket.receive_json()
            if evenement.get("type") == "webrtc_signal" and evenement.get("to"):
                await gestionnaire_live.envoyer_a(
                    session_id,
                    evenement["to"],
                    {"type": "webrtc_signal", "from": utilisateur.id, "payload": evenement.get("payload")},
                )
    except WebSocketDisconnect:
        pass
    finally:
        gestionnaire_live.deconnecter(session_id, websocket)
