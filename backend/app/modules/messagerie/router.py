from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import get_db, get_session_factory
from app.core.llm import FreeLLMClient, get_llm_client
from app.core.moderation import LIBELLES_DECISION, trier_en_arriere_plan
from app.core.deps import api_error, get_current_active_user, require_roles
from app.modules.controle_acces.router import verifier_admin_de_l_etablissement
from app.modules.etablissements.models import AdminEtablissement, AffectationEnseignant, Classe
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.messagerie.models import (
    Conversation,
    Message,
    ParticipantConversation,
    SignalementMessage,
    TypeConversation,
)
from app.modules.messagerie.schemas import (
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
    ResultatLotSignalements,
    SignalementOut,
    TraiterSignalementRequest,
    TraiterSignalementsEnLotRequest,
)

router = APIRouter(tags=["messagerie"])

_ROLES_ADULTES_STAFF = {
    RoleUtilisateur.ENSEIGNANT,
    RoleUtilisateur.ADMIN_ETABLISSEMENT,
    RoleUtilisateur.ADMIN_MINISTERIEL,
}


def _classes_ou_eleve_est_inscrit(db: Session, eleve_utilisateur_id: str) -> list[str]:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        return []
    return [
        i.classe_id
        for i in db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .all()
    ]


def _classes_ou_tuteur_a_un_enfant_inscrit(db: Session, tuteur_id: str) -> list[str]:
    eleve_ids = [e.id for e in db.query(Eleve).filter(Eleve.tuteur_id == tuteur_id).all()]
    if not eleve_ids:
        return []
    return [
        i.classe_id
        for i in db.query(Inscription)
        .filter(Inscription.eleve_id.in_(eleve_ids), Inscription.statut == StatutInscription.VALIDEE)
        .all()
    ]


def _classes_ou_enseignant_est_rattache(db: Session, enseignant_id: str) -> list[str]:
    """Groupes des seules classes effectivement affectees a l'enseignant (meme regle que
    pedagogie/evaluations) - un contrat avec l'etablissement ne donne pas acces aux
    echanges de toutes ses classes (minimisation des donnees d'eleves mineurs)."""
    return [
        a.classe_id
        for a in db.query(AffectationEnseignant).filter(AffectationEnseignant.enseignant_id == enseignant_id).all()
    ]


def _mes_classe_ids(db: Session, utilisateur: Utilisateur) -> list[str]:
    if utilisateur.role == RoleUtilisateur.ELEVE:
        return _classes_ou_eleve_est_inscrit(db, utilisateur.id)
    if utilisateur.role == RoleUtilisateur.TUTEUR:
        return _classes_ou_tuteur_a_un_enfant_inscrit(db, utilisateur.id)
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        return _classes_ou_enseignant_est_rattache(db, utilisateur.id)
    return []


def _est_participant(db: Session, utilisateur: Utilisateur, conversation: Conversation) -> bool:
    if conversation.type == TypeConversation.GROUPE_CLASSE:
        return conversation.classe_id in _mes_classe_ids(db, utilisateur)
    return (
        db.query(ParticipantConversation)
        .filter(
            ParticipantConversation.conversation_id == conversation.id,
            ParticipantConversation.utilisateur_id == utilisateur.id,
        )
        .first()
        is not None
    )


def _etablissement_actuel_eleve(db: Session, eleve_utilisateur_id: str) -> str | None:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        return None
    inscription = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )
    classe = db.get(Classe, inscription.classe_id) if inscription is not None else None
    return classe.etablissement_id if classe is not None else None


def _etablissements_concernes(db: Session, conversation: Conversation) -> set[str]:
    if conversation.type == TypeConversation.GROUPE_CLASSE:
        classe = db.get(Classe, conversation.classe_id)
        return {classe.etablissement_id} if classe else set()

    etablissements: set[str] = set()
    participants = (
        db.query(ParticipantConversation)
        .filter(ParticipantConversation.conversation_id == conversation.id)
        .all()
    )
    for participant in participants:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == participant.utilisateur_id).first()
        if eleve is None:
            continue
        inscription = (
            db.query(Inscription)
            .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
            .order_by(Inscription.created_at.desc())
            .first()
        )
        if inscription is not None:
            classe = db.get(Classe, inscription.classe_id)
            if classe is not None:
                etablissements.add(classe.etablissement_id)
    return etablissements


def _enrichir_conversation(db: Session, conversation: Conversation, utilisateur: Utilisateur) -> ConversationOut:
    base = ConversationOut.model_validate(conversation)
    if conversation.type == TypeConversation.GROUPE_CLASSE:
        classe = db.get(Classe, conversation.classe_id)
        base.classe_niveau = classe.niveau if classe else None
        return base

    autre_participation = (
        db.query(ParticipantConversation)
        .filter(
            ParticipantConversation.conversation_id == conversation.id,
            ParticipantConversation.utilisateur_id != utilisateur.id,
        )
        .first()
    )
    if autre_participation is not None:
        autre = db.get(Utilisateur, autre_participation.utilisateur_id)
        if autre is not None:
            base.autre_participant_id = autre.id
            base.autre_participant_nom = autre.nom
            base.autre_participant_prenom = autre.prenom
    return base


@router.get("/conversations", response_model=list[ConversationOut])
def mes_conversations(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> list[ConversationOut]:
    classe_ids = _mes_classe_ids(db, utilisateur)
    groupes = (
        db.query(Conversation).filter(Conversation.classe_id.in_(classe_ids)).all() if classe_ids else []
    )
    dm_ids = [
        p.conversation_id
        for p in db.query(ParticipantConversation)
        .filter(ParticipantConversation.utilisateur_id == utilisateur.id)
        .all()
    ]
    dms = db.query(Conversation).filter(Conversation.id.in_(dm_ids)).all() if dm_ids else []
    conversations = sorted(groupes + dms, key=lambda c: c.created_at, reverse=True)
    return [_enrichir_conversation(db, c, utilisateur) for c in conversations]


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def creer_conversation_dm(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> ConversationOut:
    autre = db.get(Utilisateur, payload.participant_id)
    if autre is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Utilisateur introuvable.")
    if autre.id == utilisateur.id:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "cible_invalide", "Impossible de se contacter soi-même.")

    roles = {utilisateur.role, autre.role}
    if RoleUtilisateur.ELEVE in roles and roles & _ROLES_ADULTES_STAFF:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "dm_adulte_eleve_interdit",
            "Les échanges entre un adulte et un élève passent uniquement par le groupe de classe.",
        )
    if utilisateur.role == RoleUtilisateur.ELEVE and autre.role == RoleUtilisateur.ELEVE:
        # Arbitrage du 2026-09-27 : entre eleves (souvent mineurs), la messagerie privee
        # reste interne a l'etablissement - jamais un contact avec un eleve inconnu d'ailleurs.
        mon_etablissement = _etablissement_actuel_eleve(db, utilisateur.id)
        if mon_etablissement is None or mon_etablissement != _etablissement_actuel_eleve(db, autre.id):
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "hors_etablissement",
                "Vous ne pouvez écrire qu'aux élèves de votre établissement.",
            )
    if {utilisateur.role, autre.role} == {RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR}:
        eleve_id = autre.id if autre.role == RoleUtilisateur.ELEVE else utilisateur.id
        tuteur_id = utilisateur.id if utilisateur.role == RoleUtilisateur.TUTEUR else autre.id
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_id).first()
        if eleve is None or eleve.tuteur_id != tuteur_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet élève n'est pas rattaché à ce tuteur.")

    mes_conv_ids = {
        p.conversation_id
        for p in db.query(ParticipantConversation)
        .filter(ParticipantConversation.utilisateur_id == utilisateur.id)
        .all()
    }
    ses_conv_ids = {
        p.conversation_id
        for p in db.query(ParticipantConversation)
        .filter(ParticipantConversation.utilisateur_id == autre.id)
        .all()
    }
    communes = mes_conv_ids & ses_conv_ids
    if communes:
        existante = (
            db.query(Conversation)
            .filter(Conversation.id.in_(communes), Conversation.type == TypeConversation.DM)
            .first()
        )
        if existante is not None:
            return _enrichir_conversation(db, existante, utilisateur)

    conversation = Conversation(type=TypeConversation.DM)
    db.add(conversation)
    db.flush()
    db.add(ParticipantConversation(conversation_id=conversation.id, utilisateur_id=utilisateur.id))
    db.add(ParticipantConversation(conversation_id=conversation.id, utilisateur_id=autre.id))
    db.commit()
    db.refresh(conversation)
    return _enrichir_conversation(db, conversation, utilisateur)


@router.get("/classes/{classe_id}/conversation", response_model=ConversationOut)
def obtenir_conversation_classe(
    classe_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> ConversationOut:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    conversation = db.query(Conversation).filter(Conversation.classe_id == classe_id).first()
    if conversation is None or not _est_participant(db, utilisateur, conversation):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'êtes pas membre de ce groupe de classe.")
    return _enrichir_conversation(db, conversation, utilisateur)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def lister_messages(
    conversation_id: str,
    limite: int = Query(100, ge=1, le=200),
    avant: str | None = None,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> list[MessageOut]:
    """Du plus recent au plus ancien, par pages de `limite` ; `avant` = id du plus ancien
    message deja affiche, pour charger la page precedente."""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Conversation introuvable.")
    if not _est_participant(db, utilisateur, conversation):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'êtes pas membre de cette conversation.")

    requete = db.query(Message).filter(Message.conversation_id == conversation_id)
    if avant:
        repere = db.get(Message, avant)
        if repere is None or repere.conversation_id != conversation_id:
            raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Message de référence introuvable.")
        requete = requete.filter(Message.created_at < repere.created_at)
    messages = requete.order_by(Message.created_at.desc()).limit(limite).all()
    visibles = [m for m in messages if utilisateur.id not in (m.masque_par or [])]
    auteurs = {a.id: a for a in db.query(Utilisateur).filter(Utilisateur.id.in_({m.auteur_id for m in visibles})).all()}
    resultat = []
    for m in visibles:
        sortie = MessageOut.model_validate(m)
        auteur = auteurs.get(m.auteur_id)
        if auteur is not None:
            sortie.auteur_nom = auteur.nom
            sortie.auteur_prenom = auteur.prenom
        resultat.append(sortie)
    return resultat


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
def envoyer_message(
    conversation_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> MessageOut:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Conversation introuvable.")
    if not _est_participant(db, utilisateur, conversation):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'êtes pas membre de cette conversation.")

    message = Message(conversation_id=conversation_id, auteur_id=utilisateur.id, contenu=payload.contenu)
    db.add(message)
    db.commit()
    db.refresh(message)
    sortie = MessageOut.model_validate(message)
    sortie.auteur_nom = utilisateur.nom
    sortie.auteur_prenom = utilisateur.prenom
    return sortie


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def masquer_message(
    message_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> None:
    """Suppression non destructrice (UC-13, delegue) : masque le message du seul point
    de vue de l'appelant, jamais du stockage serveur - la journalisation reste intacte
    pour signalement/preuve (Art. 519/521/550)."""
    message = db.get(Message, message_id)
    if message is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Message introuvable.")
    conversation = db.get(Conversation, message.conversation_id)
    if not _est_participant(db, utilisateur, conversation):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'êtes pas membre de cette conversation.")

    masque = list(message.masque_par or [])
    if utilisateur.id not in masque:
        masque.append(utilisateur.id)
        message.masque_par = masque
        db.commit()


@router.post("/messages/{message_id}/signaler", response_model=SignalementOut, status_code=status.HTTP_201_CREATED)
def signaler_message(
    message_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> SignalementMessage:
    """Rend le message immediatement visible a l'A+ concerne via
    GET /etablissements/{id}/signalements (liste d'ecran, meme logique que les autres
    ecrans de revision de la plateforme) plutot que d'inventer un nouveau canal
    d'e-mail non specifie."""
    message = db.get(Message, message_id)
    if message is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Message introuvable.")
    conversation = db.get(Conversation, message.conversation_id)
    if not _est_participant(db, utilisateur, conversation):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'êtes pas membre de cette conversation.")

    existant = (
        db.query(SignalementMessage)
        .filter(
            SignalementMessage.message_id == message_id,
            SignalementMessage.signale_par_id == utilisateur.id,
            SignalementMessage.traite.is_(False),
        )
        .first()
    )
    if existant is not None:
        return existant

    signalement = SignalementMessage(message_id=message_id, signale_par_id=utilisateur.id)
    db.add(signalement)
    db.commit()
    db.refresh(signalement)
    contexte = "message d'un groupe de classe" if conversation.type == TypeConversation.GROUPE_CLASSE else "message prive"
    background_tasks.add_task(
        trier_en_arriere_plan, session_factory, SignalementMessage, signalement.id, llm_client, message.contenu, contexte
    )
    return signalement


@router.get("/etablissements/{etablissement_id}/signalements", response_model=list[SignalementOut])
def signalements_en_attente(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[SignalementMessage]:
    """Les 200 signalements en attente les plus recents concernant l'etablissement. Une
    seule requete jointe (au lieu de 2 lectures par signalement du pays entier) ; seules
    les conversations privees demandent encore de resoudre l'etablissement des eleves."""
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)
    classe_ids = {c.id for c in db.query(Classe.id).filter(Classe.etablissement_id == etablissement_id)}
    pendants = (
        db.query(SignalementMessage, Conversation)
        .join(Message, Message.id == SignalementMessage.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(SignalementMessage.traite.is_(False))
        .order_by(SignalementMessage.created_at.desc())
        .all()
    )
    resultat = []
    for signalement, conversation in pendants:
        if conversation.type == TypeConversation.GROUPE_CLASSE:
            concerne = conversation.classe_id in classe_ids
        else:
            concerne = etablissement_id in _etablissements_concernes(db, conversation)
        if concerne:
            resultat.append(signalement)
            if len(resultat) >= 200:
                break
    return resultat


@router.post("/signalements/traiter-en-lot", response_model=ResultatLotSignalements)
def traiter_signalements_en_lot(
    payload: TraiterSignalementsEnLotRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ResultatLotSignalements:
    resultat = ResultatLotSignalements(traites=[], ignores=[])
    for signalement_id in payload.signalement_ids:
        signalement = db.get(SignalementMessage, signalement_id)
        if signalement is None or signalement.traite:
            resultat.ignores.append(signalement_id)
            continue
        message = db.get(Message, signalement.message_id)
        etablissements = _etablissements_concernes(db, db.get(Conversation, message.conversation_id))
        if admin.role != RoleUtilisateur.ADMIN_MINISTERIEL:
            lien_admin = db.get(AdminEtablissement, admin.id)
            if lien_admin is None or lien_admin.etablissement_id not in etablissements:
                resultat.ignores.append(signalement_id)
                continue
        decision = payload.decision or LIBELLES_DECISION.get(signalement.ia_decision)
        if decision is None:
            resultat.ignores.append(signalement_id)  # a examiner, ou pas encore trie par l'IA
            continue
        signalement.traite, signalement.decision, signalement.traite_par_id = True, decision, admin.id
        resultat.traites.append(signalement_id)
    db.commit()
    return resultat


@router.post("/signalements/{signalement_id}/traiter", response_model=SignalementOut)
def traiter_signalement(
    signalement_id: str,
    payload: TraiterSignalementRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> SignalementMessage:
    signalement = db.get(SignalementMessage, signalement_id)
    if signalement is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Signalement introuvable.")
    message = db.get(Message, signalement.message_id)
    conversation = db.get(Conversation, message.conversation_id)
    etablissements = _etablissements_concernes(db, conversation)

    if admin.role != RoleUtilisateur.ADMIN_MINISTERIEL:
        lien_admin = db.get(AdminEtablissement, admin.id)
        if lien_admin is None or lien_admin.etablissement_id not in etablissements:
            raise api_error(
                status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce signalement ne concerne pas votre établissement."
            )

    signalement.traite = True
    signalement.decision = payload.decision
    signalement.traite_par_id = admin.id
    db.commit()
    db.refresh(signalement)
    return signalement
