"""Lot 7.8 — stages (entreprises partenaires), competences metier, bourses scientifiques."""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles, verifier_portee_etablissement
from app.modules.etablissements.models import AffectationEnseignant
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve
from app.modules.insertion.models import (
    CandidatureStage,
    CompetenceMetier,
    NiveauCompetence,
    OffreStage,
    StatutCandidatureStage,
)
from app.modules.insertion.service import classe_actuelle, eligibilite_bourse_scientifique

router = APIRouter(tags=["insertion"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class OffreStageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entreprise: str = Field(min_length=2, max_length=200)
    intitule: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    lieu: str = Field(min_length=2, max_length=120)
    filiere: str | None = Field(default=None, max_length=100)
    duree_semaines: int = Field(ge=1, le=52)
    date_limite: date
    contact: str = Field(min_length=3, max_length=200)


class OffreStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    etablissement_id: str
    entreprise: str
    intitule: str
    description: str
    lieu: str
    filiere: str | None
    duree_semaines: int
    date_limite: date
    contact: str
    active: bool
    created_at: datetime
    ma_candidature: str | None = None  # statut de la candidature de l'eleve qui consulte
    nombre_candidatures: int | None = None  # vue A+


class CandidatureIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=10, max_length=3000)


class CandidatureOut(BaseModel):
    id: str
    offre_id: str
    eleve_utilisateur_id: str
    eleve_nom: str
    eleve_prenom: str
    message: str
    statut: StatutCandidatureStage
    created_at: datetime


class DecisionCandidatureIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statut: Literal["retenue", "non_retenue"]


class CompetenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intitule: str = Field(min_length=3, max_length=200)
    niveau: NiveauCompetence


class CompetenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    intitule: str
    niveau: NiveauCompetence
    valide_par_id: str
    created_at: datetime


class EligibiliteOut(BaseModel):
    eligible: bool
    moyenne_sur_20: float | None
    seuil_sur_20: float
    matieres: list[str]
    explication: str


# ─── Aides ────────────────────────────────────────────────────────────────────


def _eleve(db: Session, eleve_utilisateur_id: str) -> Eleve:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Élève introuvable.")
    return eleve


def _etablissement_de(db: Session, eleve: Eleve) -> str:
    classe = classe_actuelle(db, eleve)
    if classe is None:
        raise api_error(status.HTTP_409_CONFLICT, "aucune_inscription_validee", "Aucune inscription validée.")
    return classe.etablissement_id


def _offre(db: Session, offre_id: str) -> OffreStage:
    offre = db.get(OffreStage, offre_id)
    if offre is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Offre de stage introuvable.")
    return offre


_ADMINS = require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)


# ─── Offres de stage ──────────────────────────────────────────────────────────


@router.post("/etablissements/{etablissement_id}/stages", response_model=OffreStageOut, status_code=status.HTTP_201_CREATED)
def publier_offre(
    etablissement_id: str, payload: OffreStageIn, db: Session = Depends(get_db), admin: Utilisateur = Depends(_ADMINS)
) -> OffreStage:
    verifier_portee_etablissement(db, admin, etablissement_id)
    if payload.date_limite < date.today():
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "date_passee", "La date limite est déjà passée.")
    offre = OffreStage(etablissement_id=etablissement_id, publie_par_id=admin.id, **payload.model_dump())
    db.add(offre)
    db.commit()
    db.refresh(offre)
    return offre


@router.get("/etablissements/{etablissement_id}/stages", response_model=list[OffreStageOut])
def offres_de_l_etablissement(
    etablissement_id: str, db: Session = Depends(get_db), admin: Utilisateur = Depends(_ADMINS)
) -> list[OffreStageOut]:
    verifier_portee_etablissement(db, admin, etablissement_id)
    offres = db.query(OffreStage).filter(OffreStage.etablissement_id == etablissement_id).order_by(OffreStage.created_at.desc()).all()
    sorties = []
    for offre in offres:
        sortie = OffreStageOut.model_validate(offre)
        sortie.nombre_candidatures = db.query(CandidatureStage).filter(CandidatureStage.offre_id == offre.id).count()
        sorties.append(sortie)
    return sorties


@router.post("/stages/{offre_id}/cloturer", response_model=OffreStageOut)
def cloturer_offre(offre_id: str, db: Session = Depends(get_db), admin: Utilisateur = Depends(_ADMINS)) -> OffreStage:
    offre = _offre(db, offre_id)
    verifier_portee_etablissement(db, admin, offre.etablissement_id)
    offre.active = False
    db.commit()
    db.refresh(offre)
    return offre


@router.get("/stages", response_model=list[OffreStageOut])
def offres_pour_moi(
    db: Session = Depends(get_db), eleve_u: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> list[OffreStageOut]:
    """Offres ouvertes de l'etablissement de l'eleve (filiere compatible), candidature incluse."""
    eleve = _eleve(db, eleve_u.id)
    classe = classe_actuelle(db, eleve)
    if classe is None:
        return []
    offres = (
        db.query(OffreStage)
        .filter(
            OffreStage.etablissement_id == classe.etablissement_id,
            OffreStage.active.is_(True),
            OffreStage.date_limite >= date.today(),
        )
        .order_by(OffreStage.date_limite)
        .all()
    )
    mes = {c.offre_id: c.statut.value for c in db.query(CandidatureStage).filter(CandidatureStage.eleve_utilisateur_id == eleve_u.id)}
    sorties = []
    for offre in offres:
        if offre.filiere and classe.filiere and offre.filiere != classe.filiere:
            continue
        sortie = OffreStageOut.model_validate(offre)
        sortie.ma_candidature = mes.get(offre.id)
        sorties.append(sortie)
    return sorties


@router.post("/stages/{offre_id}/candidatures", response_model=CandidatureOut, status_code=status.HTTP_201_CREATED)
def candidater(
    offre_id: str,
    payload: CandidatureIn,
    db: Session = Depends(get_db),
    eleve_u: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> CandidatureOut:
    offre = _offre(db, offre_id)
    eleve = _eleve(db, eleve_u.id)
    if _etablissement_de(db, eleve) != offre.etablissement_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette offre est réservée aux élèves d'un autre établissement.")
    if not offre.active or offre.date_limite < date.today():
        raise api_error(status.HTTP_409_CONFLICT, "offre_close", "Cette offre n'accepte plus de candidature.")
    candidature = CandidatureStage(offre_id=offre.id, eleve_utilisateur_id=eleve_u.id, message=payload.message)
    db.add(candidature)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "deja_candidat", "Vous avez déjà postulé à cette offre.") from None
    db.refresh(candidature)
    return _candidature_out(candidature, eleve_u)


def _candidature_out(c: CandidatureStage, u: Utilisateur) -> CandidatureOut:
    return CandidatureOut(
        id=c.id, offre_id=c.offre_id, eleve_utilisateur_id=u.id, eleve_nom=u.nom, eleve_prenom=u.prenom,
        message=c.message, statut=c.statut, created_at=c.created_at,
    )


@router.get("/stages/{offre_id}/candidatures", response_model=list[CandidatureOut])
def candidatures_de_l_offre(offre_id: str, db: Session = Depends(get_db), admin: Utilisateur = Depends(_ADMINS)) -> list[CandidatureOut]:
    offre = _offre(db, offre_id)
    verifier_portee_etablissement(db, admin, offre.etablissement_id)
    lignes = (
        db.query(CandidatureStage, Utilisateur)
        .join(Utilisateur, Utilisateur.id == CandidatureStage.eleve_utilisateur_id)
        .filter(CandidatureStage.offre_id == offre_id)
        .order_by(CandidatureStage.created_at)
        .all()
    )
    return [_candidature_out(c, u) for c, u in lignes]


@router.post("/candidatures-stage/{candidature_id}/decision", response_model=CandidatureOut)
def decider_candidature(
    candidature_id: str, payload: DecisionCandidatureIn, db: Session = Depends(get_db), admin: Utilisateur = Depends(_ADMINS)
) -> CandidatureOut:
    """L'A+ transmet la decision de l'entreprise (qui n'a pas de compte)."""
    candidature = db.get(CandidatureStage, candidature_id)
    if candidature is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Candidature introuvable.")
    verifier_portee_etablissement(db, admin, _offre(db, candidature.offre_id).etablissement_id)
    candidature.statut = StatutCandidatureStage(payload.statut)
    db.commit()
    return _candidature_out(candidature, db.get(Utilisateur, candidature.eleve_utilisateur_id))


# ─── Competences metier (passeport) ───────────────────────────────────────────


@router.post(
    "/eleves/{eleve_utilisateur_id}/competences-metier", response_model=CompetenceOut, status_code=status.HTTP_201_CREATED
)
def valider_competence(
    eleve_utilisateur_id: str,
    payload: CompetenceIn,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> CompetenceMetier:
    """Seul un enseignant affecte a la classe actuelle de l'eleve valide une competence."""
    classe = classe_actuelle(db, _eleve(db, eleve_utilisateur_id))
    affecte = classe is not None and (
        db.query(AffectationEnseignant)
        .filter(AffectationEnseignant.enseignant_id == enseignant.id, AffectationEnseignant.classe_id == classe.id)
        .first()
        is not None
    )
    if not affecte:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet élève n'est pas dans une de vos classes.")
    competence = CompetenceMetier(
        eleve_utilisateur_id=eleve_utilisateur_id, intitule=payload.intitule.strip(), niveau=payload.niveau, valide_par_id=enseignant.id
    )
    db.add(competence)
    db.commit()
    db.refresh(competence)
    return competence


@router.get("/eleves/{eleve_utilisateur_id}/competences-metier", response_model=list[CompetenceOut])
def lister_competences(
    eleve_utilisateur_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR, RoleUtilisateur.ENSEIGNANT)
    ),
) -> list[CompetenceMetier]:
    eleve = _eleve(db, eleve_utilisateur_id)
    if utilisateur.role == RoleUtilisateur.ELEVE and utilisateur.id != eleve_utilisateur_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Accès refusé.")
    if utilisateur.role == RoleUtilisateur.TUTEUR and eleve.tuteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet élève n'est pas rattaché à votre compte.")
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        classe = classe_actuelle(db, eleve)
        if classe is None or db.query(AffectationEnseignant).filter(
            AffectationEnseignant.enseignant_id == utilisateur.id, AffectationEnseignant.classe_id == classe.id
        ).first() is None:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet élève n'est pas dans une de vos classes.")
    return (
        db.query(CompetenceMetier)
        .filter(CompetenceMetier.eleve_utilisateur_id == eleve_utilisateur_id)
        .order_by(CompetenceMetier.created_at.desc())
        .all()
    )


# ─── Bourses scientifiques ────────────────────────────────────────────────────


@router.get("/bourses/eligibilite-scientifique", response_model=EligibiliteOut)
def mon_eligibilite(
    eleve_utilisateur_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR)),
) -> EligibiliteOut:
    """Pre-controle affiche avant la demande (la regle est aussi appliquee a la soumission)."""
    if utilisateur.role == RoleUtilisateur.ELEVE:
        eleve = _eleve(db, utilisateur.id)
    else:
        if not eleve_utilisateur_id:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "eleve_requis", "Choisissez l'enfant concerné.")
        eleve = _eleve(db, eleve_utilisateur_id)
        if eleve.tuteur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet élève n'est pas rattaché à votre compte.")
    resultat = eligibilite_bourse_scientifique(db, eleve)
    return EligibiliteOut(**resultat.__dict__)
