from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.audit import journaliser_action_ministerielle
from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user, require_roles
from app.core.etudiant import est_etudiant
from app.modules.coffre_fort.models import ModuleDepenseCoffreFort
from app.modules.coffre_fort.service import evaluer_depense
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve
from app.modules.micro_jobs.models import (
    ContestationMicroJob,
    MissionMicroJob,
    OffreMicroJob,
    StatutContestationMicroJob,
    StatutMissionMicroJob,
    StatutOffreMicroJob,
)
from app.modules.micro_jobs.schemas import (
    ContestationMicroJobAEtrancherOut,
    ContestationMicroJobDetailOut,
    ContestationMicroJobOut,
    ContesterMissionRequest,
    DecisionContestationRequest,
    MissionAReverserOut,
    MissionMicroJobOut,
    OffreMicroJobCreate,
    OffreMicroJobOut,
    ReverserPrestataireRequest,
)
from app.modules.paiements.schemas import AmorcerPaiementRequest

router = APIRouter(tags=["micro-jobs"])

_DELAI_VALIDATION_TACITE = timedelta(days=5)

_ROLES_ADULTES = (
    RoleUtilisateur.ENSEIGNANT,
    RoleUtilisateur.TUTEUR,
    RoleUtilisateur.ADMIN_ETABLISSEMENT,
    RoleUtilisateur.ADMIN_MINISTERIEL,
)


def _est_etudiant_utilisateur(db: Session, utilisateur: Utilisateur) -> bool:
    if utilisateur.role != RoleUtilisateur.ELEVE:
        return False
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
    return eleve is not None and est_etudiant(db, eleve.id)


def _exiger_client_micro_job(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> Utilisateur:
    """UC-57 (lot admin etablissement, arbitrage utilisateur du 2026-09-26) : CLIENT
    (publier une offre, payer) ouvert aux adultes + aux etudiants (eleve inscrit et
    valide dans un etablissement UP) - un eleve EP/ES est exclu, ce qu'aucune verification
    explicite ne faisait avant ce lot (l'ancien _ROLES_CLIENT incluait tout ELEVE sans
    distinction)."""
    if utilisateur.role in _ROLES_ADULTES or _est_etudiant_utilisateur(db, utilisateur):
        return utilisateur
    raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Reserve aux adultes et aux etudiants.")


def _exiger_prestataire_micro_job(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_active_user)
) -> Utilisateur:
    """UC-57 : PRESTATAIRE (accepter une offre, etre remunere) reserve aux SEULS
    etudiants - les adultes (Enseignant/Tuteur/A+/A++), auparavant seuls roles majeurs
    autorises ici (ADR-008 addendum), en sont desormais exclus : les micro-jobs sont
    penses comme un revenu d'appoint etudiant, pas un service entre adultes de la
    plateforme (arbitrage explicite de l'utilisateur, corrige la premiere proposition du
    cahier des charges qui excluait aussi les adultes du cote CLIENT)."""
    if _est_etudiant_utilisateur(db, utilisateur):
        return utilisateur
    raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Reserve aux etudiants.")


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
    utilisateur: Utilisateur = Depends(_exiger_client_micro_job),
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
    utilisateur: Utilisateur = Depends(_exiger_client_micro_job),
) -> OffreMicroJob:
    offre = db.get(OffreMicroJob, offre_id)
    if offre is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Offre introuvable.")
    if offre.client_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette offre ne vous appartient pas.")
    if offre.statut != StatutOffreMicroJob.EN_ATTENTE_PAIEMENT:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette offre n'attend pas de paiement.")

    if utilisateur.role == RoleUtilisateur.ELEVE:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
        if eleve is not None and eleve.tuteur_id is not None:
            validation = evaluer_depense(
                db,
                tuteur_id=eleve.tuteur_id,
                eleve_utilisateur_id=utilisateur.id,
                module=ModuleDepenseCoffreFort.MICRO_JOB,
                reference_id=offre.id,
                montant=offre.prix,
            )
            if validation is not None:
                raise api_error(
                    status.HTTP_409_CONFLICT,
                    "en_attente_validation_parentale",
                    "Cette depense depasse le seuil defini par votre tuteur et attend sa validation.",
                )

    offre.kkiapay_transaction_id = payload.transaction_id
    db.commit()
    db.refresh(offre)
    return offre


@router.post("/micro-jobs/offres/{offre_id}/annuler", response_model=OffreMicroJobOut)
def annuler_offre(
    offre_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(_exiger_client_micro_job)
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
    db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(_exiger_client_micro_job)
) -> list[OffreMicroJob]:
    return db.query(OffreMicroJob).filter(OffreMicroJob.statut == StatutOffreMicroJob.OUVERTE).all()


@router.get("/micro-jobs/offres/{offre_id}", response_model=OffreMicroJobOut)
def obtenir_offre(
    offre_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(_exiger_client_micro_job)
) -> OffreMicroJob:
    offre = db.get(OffreMicroJob, offre_id)
    if offre is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Offre introuvable.")
    return offre


@router.post(
    "/micro-jobs/offres/{offre_id}/accepter", response_model=MissionMicroJobOut, status_code=status.HTTP_201_CREATED
)
def accepter_offre(
    offre_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(_exiger_prestataire_micro_job)
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
    mission_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(_exiger_prestataire_micro_job)
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
    mission_id: str, db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(_exiger_client_micro_job)
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
    utilisateur: Utilisateur = Depends(_exiger_client_micro_job),
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


@router.get("/contestations-micro-job", response_model=list[ContestationMicroJobDetailOut])
def lister_contestations_micro_job(
    statut: StatutContestationMicroJob = StatutContestationMicroJob.EN_ATTENTE,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[ContestationMicroJobDetailOut]:
    """UC-31/46 : file d'arbitrage - remplace la saisie manuelle d'un identifiant de
    contestation par une liste avec tout le contexte necessaire a la decision (montant,
    parties, motif), meme principe que la file d'arbitrage gig-economy etudiee dans le
    cahier des charges. Volume naturellement borne (une contestation par mission
    contestee) : pas de pagination serveur pour ce premier jet, a revoir si le volume
    grandit significativement."""
    contestations = (
        db.query(ContestationMicroJob)
        .filter(ContestationMicroJob.statut == statut)
        .order_by(ContestationMicroJob.created_at.asc())
        .all()
    )
    if not contestations:
        return []

    missions = {
        m.id: m
        for m in db.query(MissionMicroJob)
        .filter(MissionMicroJob.id.in_({c.mission_id for c in contestations}))
        .all()
    }
    offres = {
        o.id: o for o in db.query(OffreMicroJob).filter(OffreMicroJob.id.in_({m.offre_id for m in missions.values()}))
    }
    utilisateur_ids = {m.prestataire_id for m in missions.values()} | {o.client_id for o in offres.values()}
    utilisateurs = {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_(utilisateur_ids)).all()}

    resultat = []
    for contestation in contestations:
        mission = missions[contestation.mission_id]
        offre = offres[mission.offre_id]
        client = utilisateurs[offre.client_id]
        prestataire = utilisateurs[mission.prestataire_id]
        resultat.append(
            ContestationMicroJobDetailOut(
                id=contestation.id,
                mission_id=contestation.mission_id,
                motif=contestation.motif,
                statut=contestation.statut,
                decision_motif=contestation.decision_motif,
                created_at=contestation.created_at,
                offre_titre=offre.titre,
                prix=mission.prix_paye,
                client_nom=client.nom,
                client_prenom=client.prenom,
                prestataire_nom=prestataire.nom,
                prestataire_prenom=prestataire.prenom,
            )
        )
    return resultat


@router.get("/contestations-micro-job-en-attente", response_model=list[ContestationMicroJobAEtrancherOut])
def contestations_micro_job_en_attente(
    db: Session = Depends(get_db), _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL))
) -> list[dict]:
    """UC-18 : sans cette liste, l'admin ministeriel n'a aucun moyen de decouvrir quelles
    contestations attendent un arbitrage - seule une communication hors plateforme de
    l'identifiant permettait d'agir (voir MicroJobsArbitragePage.tsx cote frontend)."""
    contestations = (
        db.query(ContestationMicroJob).filter(ContestationMicroJob.statut == StatutContestationMicroJob.EN_ATTENTE).all()
    )
    missions = {
        m.id: m
        for m in db.query(MissionMicroJob).filter(MissionMicroJob.id.in_({c.mission_id for c in contestations}))
    } if contestations else {}
    offres = {
        o.id: o for o in db.query(OffreMicroJob).filter(OffreMicroJob.id.in_({m.offre_id for m in missions.values()}))
    } if missions else {}
    resultats = []
    for contestation in contestations:
        mission = missions.get(contestation.mission_id)
        offre = offres.get(mission.offre_id) if mission is not None else None
        resultats.append(
            {
                "id": contestation.id,
                "mission_id": contestation.mission_id,
                "motif": contestation.motif,
                "statut": contestation.statut,
                "decision_motif": contestation.decision_motif,
                "created_at": contestation.created_at,
                "offre_titre": offre.titre if offre is not None else "Offre introuvable",
                "offre_prix": offre.prix if offre is not None else 0.0,
            }
        )
    return resultats


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
    journaliser_action_ministerielle(
        db, admin, f"micro_job.contestation.{payload.decision.value}", "contestation_micro_job", contestation.id,
        payload.decision_motif,
    )
    db.commit()
    db.refresh(contestation)
    return contestation


@router.get("/missions-micro-job/a-reverser", response_model=list[MissionAReverserOut])
def lister_missions_a_reverser(
    db: Session = Depends(get_db), _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL))
) -> list[MissionAReverserOut]:
    """UC-33/48 : file des missions validees pas encore reversees, avec le contact
    mobile money deja connu du prestataire (Utilisateur.telephone) - remplace la saisie
    manuelle d'un identifiant de mission."""
    # La validation tacite (client silencieux 5 jours) n'etait appliquee qu'a l'occasion
    # d'une action sur la mission : un prestataire dont le client ne repondait jamais
    # n'apparaissait donc jamais dans cette file, et n'etait jamais paye.
    for mission_echue in (
        db.query(MissionMicroJob)
        .filter(
            MissionMicroJob.statut == StatutMissionMicroJob.TERMINEE_DECLAREE,
            MissionMicroJob.date_limite_validation.isnot(None),
        )
        .all()
    ):
        _appliquer_validation_tacite(db, mission_echue)

    missions = (
        db.query(MissionMicroJob)
        .filter(
            MissionMicroJob.statut == StatutMissionMicroJob.VALIDEE,
            MissionMicroJob.reference_paiement_prestataire.is_(None),
        )
        .order_by(MissionMicroJob.date_declaration_fin.asc())
        .all()
    )
    if not missions:
        return []

    offres = {o.id: o for o in db.query(OffreMicroJob).filter(OffreMicroJob.id.in_({m.offre_id for m in missions}))}
    prestataires = {
        u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_({m.prestataire_id for m in missions})).all()
    }
    return [
        MissionAReverserOut(
            id=m.id,
            offre_titre=offres[m.offre_id].titre,
            prix_paye=m.prix_paye,
            prestataire_id=m.prestataire_id,
            prestataire_nom=prestataires[m.prestataire_id].nom,
            prestataire_prenom=prestataires[m.prestataire_id].prenom,
            prestataire_telephone=prestataires[m.prestataire_id].telephone,
            date_declaration_fin=m.date_declaration_fin,
        )
        for m in missions
    ]


@router.post("/missions-micro-job/{mission_id}/reverser-prestataire", response_model=MissionMicroJobOut)
def reverser_prestataire(
    mission_id: str,
    payload: ReverserPrestataireRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> MissionMicroJob:
    mission = db.get(MissionMicroJob, mission_id)
    if mission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Mission introuvable.")
    mission = _appliquer_validation_tacite(db, mission)
    if mission.statut != StatutMissionMicroJob.VALIDEE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Cette mission n'est pas prete a etre reversee.")

    mission.reference_paiement_prestataire = payload.reference_paiement
    mission.statut = StatutMissionMicroJob.PAYEE
    journaliser_action_ministerielle(
        db, admin, "micro_job.reverser", "mission_micro_job", mission.id, f"reference={payload.reference_paiement}"
    )
    db.commit()
    db.refresh(mission)
    return mission


@router.get("/mes-missions-micro-job", response_model=list[MissionMicroJobOut])
def mes_missions(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(_exiger_client_micro_job)
) -> list[MissionMicroJob]:
    mes_offre_ids = [o.id for o in db.query(OffreMicroJob).filter(OffreMicroJob.client_id == utilisateur.id).all()]
    query = db.query(MissionMicroJob).filter(
        or_(MissionMicroJob.prestataire_id == utilisateur.id, MissionMicroJob.offre_id.in_(mes_offre_ids or [""]))
    )
    return query.order_by(MissionMicroJob.created_at.desc()).all()
