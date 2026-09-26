from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, require_roles
from app.modules.controle_acces.models import ServiceControle
from app.modules.controle_acces.router import est_controleur_designe, verifier_admin_de_l_etablissement
from app.modules.etablissements.models import Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve
from app.modules.paiements.schemas import AmorcerPaiementRequest
from app.modules.services_scolaires.models import (
    LigneTransport,
    StatutTicket,
    TicketCantine,
    TicketTransport,
    TypeRepasCantine,
)
from app.modules.services_scolaires.schemas import (
    LigneTransportCreate,
    LigneTransportOut,
    TicketCantineCreate,
    TicketCantineOut,
    TicketTransportCreate,
    TicketTransportOut,
    TypeRepasCantineCreate,
    TypeRepasCantineOut,
)

router = APIRouter(tags=["services-scolaires"])


def _resoudre_beneficiaire(db: Session, utilisateur: Utilisateur, eleve_utilisateur_id: str | None) -> Utilisateur:
    """UC-11/UC-12 : le beneficiaire d'un ticket est toujours l'eleve (le service est
    rendu a lui, pas au tuteur qui peut l'acheter en son nom) - meme schema que
    DemandeActeCreate.eleve_utilisateur_id (UC-10)."""
    if utilisateur.role == RoleUtilisateur.ELEVE:
        return utilisateur
    if not eleve_utilisateur_id:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "eleve_requis", "eleve_utilisateur_id est requis pour un tuteur."
        )
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None or eleve.tuteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte.")
    return db.get(Utilisateur, eleve_utilisateur_id)


def _verifier_proprietaire_ou_tuteur(db: Session, utilisateur: Utilisateur, beneficiaire_id: str) -> None:
    if utilisateur.id == beneficiaire_id:
        return
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == beneficiaire_id).first()
    if eleve is not None and eleve.tuteur_id == utilisateur.id:
        return
    raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce ticket ne vous appartient pas.")


def _mes_eleve_utilisateur_ids(db: Session, utilisateur: Utilisateur) -> list[str]:
    if utilisateur.role == RoleUtilisateur.ELEVE:
        return [utilisateur.id]
    return [
        e.utilisateur_id
        for e in db.query(Eleve).filter(Eleve.tuteur_id == utilisateur.id).all()
        if e.utilisateur_id is not None
    ]


def _limite_remboursement_veille_18h(jour: date) -> datetime:
    veille = jour - timedelta(days=1)
    return datetime.combine(veille, time(18, 0), tzinfo=timezone.utc)


# --- Transport (UC-11) --------------------------------------------------------------


@router.post(
    "/etablissements/{etablissement_id}/lignes-transport",
    response_model=LigneTransportOut,
    status_code=status.HTTP_201_CREATED,
)
def creer_ligne_transport(
    etablissement_id: str,
    payload: LigneTransportCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> LigneTransport:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)

    ligne = LigneTransport(
        etablissement_id=etablissement_id,
        nom=payload.nom,
        prix=payload.prix,
        capacite_par_trajet=payload.capacite_par_trajet,
    )
    db.add(ligne)
    db.commit()
    db.refresh(ligne)
    return ligne


@router.get("/etablissements/{etablissement_id}/lignes-transport", response_model=list[LigneTransportOut])
def lister_lignes_transport(
    etablissement_id: str,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(get_current_active_user),
) -> list[LigneTransport]:
    return db.query(LigneTransport).filter(LigneTransport.etablissement_id == etablissement_id).all()


@router.post(
    "/lignes-transport/{ligne_id}/tickets", response_model=TicketTransportOut, status_code=status.HTTP_201_CREATED
)
def acheter_ticket_transport(
    ligne_id: str,
    payload: TicketTransportCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> TicketTransport:
    ligne = db.get(LigneTransport, ligne_id)
    if ligne is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ligne de transport introuvable.")
    beneficiaire = _resoudre_beneficiaire(db, utilisateur, payload.eleve_utilisateur_id)

    deja_pris = (
        db.query(TicketTransport)
        .filter(
            TicketTransport.ligne_id == ligne_id,
            TicketTransport.date_trajet == payload.date_trajet,
            TicketTransport.statut.in_([StatutTicket.ACHETE, StatutTicket.VALIDE]),
        )
        .count()
    )
    if deja_pris >= ligne.capacite_par_trajet:
        raise api_error(status.HTTP_409_CONFLICT, "capacite_atteinte", "Cette ligne est complete pour cette date.")

    ticket = TicketTransport(
        ligne_id=ligne_id,
        utilisateur_id=beneficiaire.id,
        date_trajet=payload.date_trajet,
        prix_paye=ligne.prix,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/tickets-transport/{ticket_id}/paiement/amorcer", response_model=TicketTransportOut)
def amorcer_paiement_ticket_transport(
    ticket_id: str,
    payload: AmorcerPaiementRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> TicketTransport:
    ticket = db.get(TicketTransport, ticket_id)
    if ticket is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ticket introuvable.")
    _verifier_proprietaire_ou_tuteur(db, utilisateur, ticket.utilisateur_id)
    if ticket.statut != StatutTicket.ACHETE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce ticket n'attend pas de paiement.")

    ticket.kkiapay_transaction_id = payload.transaction_id
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/tickets-transport/{ticket_id}/valider", response_model=TicketTransportOut)
def valider_ticket_transport(
    ticket_id: str,
    db: Session = Depends(get_db),
    controleur: Utilisateur = Depends(get_current_active_user),
) -> TicketTransport:
    ticket = db.get(TicketTransport, ticket_id)
    if ticket is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ticket introuvable.")
    ligne = db.get(LigneTransport, ticket.ligne_id)
    if not est_controleur_designe(db, controleur.id, ligne.etablissement_id, ServiceControle.TRANSPORT):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas controleur designe sur cette ligne.")
    if ticket.statut != StatutTicket.ACHETE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce ticket ne peut pas etre valide.")
    if not ticket.paiement_confirme:
        raise api_error(status.HTTP_409_CONFLICT, "paiement_non_confirme", "Le paiement de ce ticket n'est pas confirme.")

    ticket.statut = StatutTicket.VALIDE
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/tickets-transport/{ticket_id}/rembourser", response_model=TicketTransportOut)
def rembourser_ticket_transport(
    ticket_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> TicketTransport:
    ticket = db.get(TicketTransport, ticket_id)
    if ticket is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ticket introuvable.")
    _verifier_proprietaire_ou_tuteur(db, utilisateur, ticket.utilisateur_id)
    if ticket.statut != StatutTicket.ACHETE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce ticket ne peut plus etre rembourse.")
    if datetime.now(timezone.utc) > _limite_remboursement_veille_18h(ticket.date_trajet):
        raise api_error(status.HTTP_409_CONFLICT, "delai_depasse", "Le delai de remboursement est depasse.")

    ticket.statut = StatutTicket.REMBOURSE
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets-transport/{ticket_id}", response_model=TicketTransportOut)
def obtenir_ticket_transport(
    ticket_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> TicketTransport:
    ticket = db.get(TicketTransport, ticket_id)
    if ticket is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ticket introuvable.")
    ligne = db.get(LigneTransport, ticket.ligne_id)
    est_proprietaire = ticket.utilisateur_id == utilisateur.id
    est_tuteur = (
        db.query(Eleve).filter(Eleve.utilisateur_id == ticket.utilisateur_id, Eleve.tuteur_id == utilisateur.id).first()
        is not None
    )
    est_controleur = est_controleur_designe(db, utilisateur.id, ligne.etablissement_id, ServiceControle.TRANSPORT)
    est_admin = utilisateur.role in (RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    if not (est_proprietaire or est_tuteur or est_controleur or est_admin):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce ticket ne vous appartient pas.")
    if est_admin and not est_proprietaire and not est_tuteur:
        verifier_admin_de_l_etablissement(db, utilisateur, ligne.etablissement_id)
    return ticket


@router.get("/mes-tickets-transport", response_model=list[TicketTransportOut])
def mes_tickets_transport(
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> list[TicketTransport]:
    eleve_ids = _mes_eleve_utilisateur_ids(db, utilisateur)
    if not eleve_ids:
        return []
    return (
        db.query(TicketTransport)
        .filter(TicketTransport.utilisateur_id.in_(eleve_ids))
        .order_by(TicketTransport.date_trajet.desc())
        .all()
    )


# --- Cantine (UC-12) ----------------------------------------------------------------


@router.post(
    "/etablissements/{etablissement_id}/types-repas-cantine",
    response_model=TypeRepasCantineOut,
    status_code=status.HTTP_201_CREATED,
)
def creer_type_repas_cantine(
    etablissement_id: str,
    payload: TypeRepasCantineCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> TypeRepasCantine:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Etablissement introuvable.")
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)

    type_repas = TypeRepasCantine(
        etablissement_id=etablissement_id,
        nom=payload.nom,
        prix=payload.prix,
        capacite_par_jour=payload.capacite_par_jour,
    )
    db.add(type_repas)
    db.commit()
    db.refresh(type_repas)
    return type_repas


@router.get(
    "/etablissements/{etablissement_id}/types-repas-cantine", response_model=list[TypeRepasCantineOut]
)
def lister_types_repas_cantine(
    etablissement_id: str,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(get_current_active_user),
) -> list[TypeRepasCantine]:
    return db.query(TypeRepasCantine).filter(TypeRepasCantine.etablissement_id == etablissement_id).all()


@router.post(
    "/types-repas-cantine/{type_repas_id}/tickets",
    response_model=TicketCantineOut,
    status_code=status.HTTP_201_CREATED,
)
def acheter_ticket_cantine(
    type_repas_id: str,
    payload: TicketCantineCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> TicketCantine:
    type_repas = db.get(TypeRepasCantine, type_repas_id)
    if type_repas is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Type de repas introuvable.")
    beneficiaire = _resoudre_beneficiaire(db, utilisateur, payload.eleve_utilisateur_id)

    deja_pris = (
        db.query(TicketCantine)
        .filter(
            TicketCantine.type_repas_id == type_repas_id,
            TicketCantine.date_service == payload.date_service,
            TicketCantine.statut.in_([StatutTicket.ACHETE, StatutTicket.VALIDE]),
        )
        .count()
    )
    if deja_pris >= type_repas.capacite_par_jour:
        raise api_error(status.HTTP_409_CONFLICT, "capacite_atteinte", "Ce service est complet pour cette date.")

    ticket = TicketCantine(
        type_repas_id=type_repas_id,
        utilisateur_id=beneficiaire.id,
        date_service=payload.date_service,
        prix_paye=type_repas.prix,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/tickets-cantine/{ticket_id}/paiement/amorcer", response_model=TicketCantineOut)
def amorcer_paiement_ticket_cantine(
    ticket_id: str,
    payload: AmorcerPaiementRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> TicketCantine:
    ticket = db.get(TicketCantine, ticket_id)
    if ticket is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ticket introuvable.")
    _verifier_proprietaire_ou_tuteur(db, utilisateur, ticket.utilisateur_id)
    if ticket.statut != StatutTicket.ACHETE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce ticket n'attend pas de paiement.")

    ticket.kkiapay_transaction_id = payload.transaction_id
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/tickets-cantine/{ticket_id}/valider", response_model=TicketCantineOut)
def valider_ticket_cantine(
    ticket_id: str,
    db: Session = Depends(get_db),
    controleur: Utilisateur = Depends(get_current_active_user),
) -> TicketCantine:
    ticket = db.get(TicketCantine, ticket_id)
    if ticket is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ticket introuvable.")
    type_repas = db.get(TypeRepasCantine, ticket.type_repas_id)
    if not est_controleur_designe(db, controleur.id, type_repas.etablissement_id, ServiceControle.CANTINE):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'etes pas controleur designe sur ce service.")
    if ticket.statut != StatutTicket.ACHETE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce ticket ne peut pas etre valide.")
    if not ticket.paiement_confirme:
        raise api_error(status.HTTP_409_CONFLICT, "paiement_non_confirme", "Le paiement de ce ticket n'est pas confirme.")

    ticket.statut = StatutTicket.VALIDE
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/tickets-cantine/{ticket_id}/rembourser", response_model=TicketCantineOut)
def rembourser_ticket_cantine(
    ticket_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> TicketCantine:
    ticket = db.get(TicketCantine, ticket_id)
    if ticket is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ticket introuvable.")
    _verifier_proprietaire_ou_tuteur(db, utilisateur, ticket.utilisateur_id)
    if ticket.statut != StatutTicket.ACHETE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce ticket ne peut plus etre rembourse.")
    if datetime.now(timezone.utc) > _limite_remboursement_veille_18h(ticket.date_service):
        raise api_error(status.HTTP_409_CONFLICT, "delai_depasse", "Le delai de remboursement est depasse.")

    ticket.statut = StatutTicket.REMBOURSE
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets-cantine/{ticket_id}", response_model=TicketCantineOut)
def obtenir_ticket_cantine(
    ticket_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> TicketCantine:
    ticket = db.get(TicketCantine, ticket_id)
    if ticket is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Ticket introuvable.")
    type_repas = db.get(TypeRepasCantine, ticket.type_repas_id)
    est_proprietaire = ticket.utilisateur_id == utilisateur.id
    est_tuteur = (
        db.query(Eleve).filter(Eleve.utilisateur_id == ticket.utilisateur_id, Eleve.tuteur_id == utilisateur.id).first()
        is not None
    )
    est_controleur = est_controleur_designe(db, utilisateur.id, type_repas.etablissement_id, ServiceControle.CANTINE)
    est_admin = utilisateur.role in (RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    if not (est_proprietaire or est_tuteur or est_controleur or est_admin):
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce ticket ne vous appartient pas.")
    if est_admin and not est_proprietaire and not est_tuteur:
        verifier_admin_de_l_etablissement(db, utilisateur, type_repas.etablissement_id)
    return ticket


@router.get("/mes-tickets-cantine", response_model=list[TicketCantineOut])
def mes_tickets_cantine(
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> list[TicketCantine]:
    eleve_ids = _mes_eleve_utilisateur_ids(db, utilisateur)
    if not eleve_ids:
        return []
    return (
        db.query(TicketCantine)
        .filter(TicketCantine.utilisateur_id.in_(eleve_ids))
        .order_by(TicketCantine.date_service.desc())
        .all()
    )
