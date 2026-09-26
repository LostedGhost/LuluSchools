from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.micro_jobs.models import (
    ContestationMicroJob,
    MissionMicroJob,
    OffreMicroJob,
    StatutContestationMicroJob,
    StatutMissionMicroJob,
    StatutOffreMicroJob,
)
from app.modules.micro_jobs.schemas import (
    ContestationMicroJobOut,
    ContesterMissionRequest,
    DecisionContestationRequest,
    MissionMicroJobOut,
    OffreMicroJobCreate,
    OffreMicroJobOut,
    ReverserPrestataireRequest,
)
from app.modules.paiements.schemas import AmorcerPaiementRequest

router = APIRouter(tags=["micro-jobs"])

_DELAI_VALIDATION_TACITE = timedelta(days=5)

# Cote CLIENT (publier une offre, la payer, valider/contester le travail rendu) :
# ouvert a tous les roles authentifies, Eleve inclus - payer pour un service ne pose
# pas de question d'age minimum de travail (voir OffreMicroJob docstring, ADR-008 addendum).
_ROLES_CLIENT = (
    RoleUtilisateur.ENSEIGNANT,
    RoleUtilisateur.TUTEUR,
    RoleUtilisateur.ADMIN_ETABLISSEMENT,
    RoleUtilisateur.ADMIN_MINISTERIEL,
    RoleUtilisateur.ELEVE,
)
# Cote PRESTATAIRE (accepter une offre, etre remunere pour le travail) : Eleve exclu.
_ROLES_PRESTATAIRE = (
    RoleUtilisateur.ENSEIGNANT,
    RoleUtilisateur.TUTEUR,
    RoleUtilisateur.ADMIN_ETABLISSEMENT,
    RoleUtilisateur.ADMIN_MINISTERIEL,
)


def _aware_utc(moment: datetime) -> datetime:
    """SQLite (tests) ne conserve pas le fuseau horaire des colonnes DateTime(timezone=True)."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _appliquer_validation_tacite(db: Session, mission: MissionMicroJob) -> MissionMicroJob:
    if (
        mission.statut == StatutMissionMicroJob.TERMINEE_DECLAREE
        and mission.date_limite_validation is not None
        and datetime.now(timezone.utc) > _aware_utc(mission.date_limite_validation)
    ):
        mission.statut = StatutMissionMicroJob.VALIDEE
        db.commit()
        db.refresh(mission)
    return mission


@router.post("/micro-jobs/offres", response_model=OffreMicroJobOut, status_code=status.HTTP_201_CREATED)
def creer_offre(
    payload: OffreMicroJobCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(*_ROLES_CLIENT)),
) -> OffreMicroJob:
    """UC-18 : publier une offre = se declarer CLIENT et s'engager a payer. L'offre
    n'est visible des prestataires qu'une fois le paiement confirme (voir
    amorcer_paiement_offre / webhook Kkiapay)."""
    offre = OffreMicroJob(
        client_id=utilisateur.id, titre=payload.titre, description=payload.description, prix=payload.prix
    )
    db.add(offre)
    db.commit()
    db.refresh(offre)
    return offre


@router.post("/micro-jobs/offres/{offre_id}/paiement/amorcer", response_model=OffreMicroJobOut)
def amorcer_paiement_offre(
    offre_id: str,
    payload: AmorcerPaiementRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(*_ROLES_CLIENT)),
) -> OffreMicroJob:
    offre = db.get(OffreMicroJob, offre_id)
    if offre is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Offre introuvable.")
    if offre.client_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette offre ne vous appartient pas.")
    if offre.statut != StatutOffreMicroJob.EN_ATTENTE_PAIEMENT:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette offre n'attend pas de paiement.")

    offre.kkiapay_transaction_id = payload.transaction_id
    db.commit()
    db.refresh(offre)
    return offre


@router.post("/micro-jobs/offres/{offre_id}/annuler", response_model=OffreMicroJobOut)
def annuler_offre(
    offre_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(*_ROLES_CLIENT))
) -> OffreMicroJob:
    """Annulation reservee a une offre pas encore payee - une fois le paiement
    confirme (OUVERTE), l'offre suit le circuit normal (acceptation ou reste ouverte)."""
    offre = db.get(OffreMicroJob, offre_id)
    if offre is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Offre introuvable.")
    if offre.client_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette offre ne vous appartient pas.")
    if offre.statut != StatutOffreMicroJob.EN_ATTENTE_PAIEMENT:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette offre ne peut plus etre annulee.")

    offre.statut = StatutOffreMicroJob.ANNULEE
    db.commit()
    db.refresh(offre)
    return offre


@router.get("/micro-jobs/offres", response_model=list[OffreMicroJobOut])
def lister_offres(
    db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(require_roles(*_ROLES_CLIENT))
) -> list[OffreMicroJob]:
    return db.query(OffreMicroJob).filter(OffreMicroJob.statut == StatutOffreMicroJob.OUVERTE).all()


@router.get("/micro-jobs/offres/{offre_id}", response_model=OffreMicroJobOut)
def obtenir_offre(
    offre_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(require_roles(*_ROLES_CLIENT))
) -> OffreMicroJob:
    offre = db.get(OffreMicroJob, offre_id)
    if offre is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Offre introuvable.")
    return offre


@router.post(
    "/micro-jobs/offres/{offre_id}/accepter", response_model=MissionMicroJobOut, status_code=status.HTTP_201_CREATED
)
def accepter_offre(
    offre_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(*_ROLES_PRESTATAIRE))
) -> MissionMicroJob:
    """Accepter = devenir le PRESTATAIRE remunere. Reserve aux roles majeurs (Eleve
    exclu, voir ADR-008). Le paiement est deja confirme depuis la publication de
    l'offre : la mission demarre directement EN_COURS, sans etape de paiement propre."""
    offre = db.get(OffreMicroJob, offre_id)
    if offre is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Offre introuvable.")
    if offre.client_id == utilisateur.id:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Vous ne pouvez pas accepter votre propre offre.")
    if offre.statut != StatutOffreMicroJob.OUVERTE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette offre n'est plus ouverte.")

    offre.statut = StatutOffreMicroJob.FERMEE
    mission = MissionMicroJob(
        offre_id=offre_id,
        prestataire_id=utilisateur.id,
        prix_paye=offre.prix,
        paiement_confirme=True,
        kkiapay_transaction_id=offre.kkiapay_transaction_id,
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


@router.post("/missions-micro-job/{mission_id}/declarer-fin", response_model=MissionMicroJobOut)
def declarer_fin_mission(
    mission_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(*_ROLES_PRESTATAIRE))
) -> MissionMicroJob:
    mission = db.get(MissionMicroJob, mission_id)
    if mission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Mission introuvable.")
    if mission.prestataire_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette mission ne vous appartient pas.")
    if mission.statut != StatutMissionMicroJob.EN_COURS:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette mission ne peut pas etre declaree terminee.")

    mission.statut = StatutMissionMicroJob.TERMINEE_DECLAREE
    mission.date_declaration_fin = datetime.now(timezone.utc)
    mission.date_limite_validation = mission.date_declaration_fin + _DELAI_VALIDATION_TACITE
    db.commit()
    db.refresh(mission)
    return mission


@router.post("/missions-micro-job/{mission_id}/valider", response_model=MissionMicroJobOut)
def valider_mission(
    mission_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(*_ROLES_CLIENT))
) -> MissionMicroJob:
    mission = db.get(MissionMicroJob, mission_id)
    if mission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Mission introuvable.")
    offre = db.get(OffreMicroJob, mission.offre_id)
    if offre.client_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette mission ne vous appartient pas.")
    mission = _appliquer_validation_tacite(db, mission)
    if mission.statut != StatutMissionMicroJob.TERMINEE_DECLAREE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette mission ne peut pas etre validee.")

    mission.statut = StatutMissionMicroJob.VALIDEE
    db.commit()
    db.refresh(mission)
    return mission


@router.post("/missions-micro-job/{mission_id}/contester", response_model=ContestationMicroJobOut, status_code=status.HTTP_201_CREATED)
def contester_mission(
    mission_id: str,
    payload: ContesterMissionRequest,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(*_ROLES_CLIENT)),
) -> ContestationMicroJob:
    mission = db.get(MissionMicroJob, mission_id)
    if mission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Mission introuvable.")
    offre = db.get(OffreMicroJob, mission.offre_id)
    if offre.client_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette mission ne vous appartient pas.")
    mission = _appliquer_validation_tacite(db, mission)
    if mission.statut != StatutMissionMicroJob.TERMINEE_DECLAREE:
        raise api_error(
            status.HTTP_409_CONFLICT, "statut_invalide", "Cette mission ne peut plus etre contestee (delai depasse ou statut invalide)."
        )

    mission.statut = StatutMissionMicroJob.CONTESTEE
    contestation = ContestationMicroJob(mission_id=mission_id, motif=payload.motif)
    db.add(contestation)
    db.commit()
    db.refresh(contestation)
    return contestation


@router.post("/contestations-micro-job/{contestation_id}/decision", response_model=ContestationMicroJobOut)
def decider_contestation(
    contestation_id: str,
    payload: DecisionContestationRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ContestationMicroJob:
    contestation = db.get(ContestationMicroJob, contestation_id)
    if contestation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contestation introuvable.")
    if contestation.statut != StatutContestationMicroJob.EN_ATTENTE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette contestation a deja ete tranchee.")
    if payload.decision == StatutContestationMicroJob.REJETEE and not payload.decision_motif:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "motif_requis", "Un motif est requis en cas de rejet.")
    if payload.decision not in (StatutContestationMicroJob.ACCEPTEE, StatutContestationMicroJob.REJETEE):
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "decision_invalide", "Decision invalide.")

    mission = db.get(MissionMicroJob, contestation.mission_id)
    contestation.statut = payload.decision
    contestation.decision_motif = payload.decision_motif
    contestation.decision_par_id = admin.id
    mission.statut = (
        StatutMissionMicroJob.REMBOURSEE
        if payload.decision == StatutContestationMicroJob.ACCEPTEE
        else StatutMissionMicroJob.VALIDEE
    )
    db.commit()
    db.refresh(contestation)
    return contestation


@router.post("/missions-micro-job/{mission_id}/reverser-prestataire", response_model=MissionMicroJobOut)
def reverser_prestataire(
    mission_id: str,
    payload: ReverserPrestataireRequest,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> MissionMicroJob:
    mission = db.get(MissionMicroJob, mission_id)
    if mission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Mission introuvable.")
    mission = _appliquer_validation_tacite(db, mission)
    if mission.statut != StatutMissionMicroJob.VALIDEE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette mission n'est pas prete a etre reversee.")

    mission.reference_paiement_prestataire = payload.reference_paiement
    mission.statut = StatutMissionMicroJob.PAYEE
    db.commit()
    db.refresh(mission)
    return mission


@router.get("/mes-missions-micro-job", response_model=list[MissionMicroJobOut])
def mes_missions(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(*_ROLES_CLIENT))
) -> list[MissionMicroJob]:
    mes_offre_ids = [o.id for o in db.query(OffreMicroJob).filter(OffreMicroJob.client_id == utilisateur.id).all()]
    query = db.query(MissionMicroJob).filter(
        or_(MissionMicroJob.prestataire_id == utilisateur.id, MissionMicroJob.offre_id.in_(mes_offre_ids or [""]))
    )
    return query.order_by(MissionMicroJob.created_at.desc()).all()
