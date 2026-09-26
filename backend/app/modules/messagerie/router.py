from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, require_roles
from app.modules.controle_acces.router import verifier_admin_de_l_etablissement
from app.modules.etablissements.models import AdminEtablissement, Classe
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
    SignalementOut,
    TraiterSignalementRequest,
)
from app.modules.recrutement.models import Contrat, StatutContrat

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
    etablissement_ids = [
        c.etablissement_id
        for c in db.query(Contrat)
        .filter(Contrat.enseignant_id == enseignant_id, Contrat.statut == StatutContrat.SIGNE)
        .all()
    ]
    if not etablissement_ids:
        return []
    return [c.id for c in db.query(Classe).filter(Classe.etablissement_id.in_(etablissement_ids)).all()]


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
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "cible_invalide", "Impossible de se contacter soi-meme.")

    roles = {utilisateur.role, autre.role}
    if RoleUtilisateur.ELEVE in roles and roles & _ROLES_ADULTES_STAFF:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "dm_adulte_eleve_interdit",
            "Les echanges entre un adulte et un eleve passent uniquement par le groupe de classe.",
        )
    if {utilisateur.role, autre.role} == {RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR}:
        eleve_id = autre.id if autre.role == RoleUtilisateur.ELEVE else utilisateur.id
        tuteur_id = utilisateur.id if utilisateur.role == RoleUtilisateur.TUTEUR else autre.id
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_id).first()
        if eleve is None or eleve.tuteur_id != tuteur_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a ce tuteur.")

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
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas membre de ce groupe de classe.")
    return _enrichir_conversation(db, conversation, utilisateur)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def lister_messages(
    conversation_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> list[MessageOut]:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Conversation introuvable.")
    if not _est_participant(db, utilisateur, conversation):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas membre de cette conversation.")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .all()
    )
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
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas membre de cette conversation.")

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
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas membre de cette conversation.")

    masque = list(message.masque_par or [])
    if utilisateur.id not in masque:
        masque.append(utilisateur.id)
        message.masque_par = masque
        db.commit()


@router.post("/messages/{message_id}/signaler", response_model=SignalementOut, status_code=status.HTTP_201_CREATED)
def signaler_message(
    message_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
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
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas membre de cette conversation.")

    signalement = SignalementMessage(message_id=message_id, signale_par_id=utilisateur.id)
    db.add(signalement)
    db.commit()
    db.refresh(signalement)
    return signalement


@router.get("/etablissements/{etablissement_id}/signalements", response_model=list[SignalementOut])
def signalements_en_attente(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[SignalementMessage]:
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)
    pendants = db.query(SignalementMessage).filter(SignalementMessage.traite.is_(False)).all()
    resultat = []
    for signalement in pendants:
        message = db.get(Message, signalement.message_id)
        conversation = db.get(Conversation, message.conversation_id)
        if etablissement_id in _etablissements_concernes(db, conversation):
            resultat.append(signalement)
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
                status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce signalement ne concerne pas votre etablissement."
            )

    signalement.traite = True
    signalement.decision = payload.decision
    signalement.traite_par_id = admin.id
    db.commit()
    db.refresh(signalement)
    return signalement
