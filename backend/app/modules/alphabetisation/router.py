"""Lot 7.7 — alphabetisation et education des adultes (PAG 2021-2026, axe 5, action 4)."""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles, verifier_portee_etablissement
from app.modules.alphabetisation.models import InscriptionAlphabetisation
from app.modules.etablissements.models import Classe, Etablissement, TypeEtablissement, annee_academique_courante
from app.modules.identite.models import RoleUtilisateur, Utilisateur

router = APIRouter(tags=["alphabetisation"])


class ClasseAlphabetisationOut(BaseModel):
    classe_id: str
    niveau: str
    centre_id: str
    centre_nom: str
    departement: str | None
    commune: str | None
    places_restantes: int
    inscrit: bool


class InscriptionAlphabetisationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classe_id: str = Field(max_length=36)


class ApprenantOut(BaseModel):
    utilisateur_id: str
    nom: str
    prenom: str
    telephone: str | None
    classe_id: str
    niveau: str
    inscrit_le: datetime


def _nombre_inscrits(db: Session, classe_id: str) -> int:
    return (
        db.query(func.count(InscriptionAlphabetisation.id)).filter(InscriptionAlphabetisation.classe_id == classe_id).scalar()
        or 0
    )


def _sortie(db: Session, classe: Classe, etab: Etablissement, inscrit: bool) -> ClasseAlphabetisationOut:
    return ClasseAlphabetisationOut(
        classe_id=classe.id, niveau=classe.niveau, centre_id=etab.id, centre_nom=etab.nom,
        departement=etab.departement, commune=etab.commune,
        places_restantes=max(0, classe.capacite - _nombre_inscrits(db, classe.id)), inscrit=inscrit,
    )


@router.get("/alphabetisation/classes", response_model=list[ClasseAlphabetisationOut])
def classes_ouvertes(
    db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR))
) -> list[ClasseAlphabetisationOut]:
    """Classes des centres d'alphabetisation actifs pour l'annee en cours (les siennes en tete)."""
    mes_classes = {
        c
        for (c,) in db.query(InscriptionAlphabetisation.classe_id).filter(
            InscriptionAlphabetisation.utilisateur_id == utilisateur.id
        )
    }
    lignes = (
        db.query(Classe, Etablissement)
        .join(Etablissement, Etablissement.id == Classe.etablissement_id)
        .filter(
            Etablissement.type == TypeEtablissement.CA,
            Etablissement.actif.is_(True),
            Classe.annee_academique == annee_academique_courante(),
        )
        .order_by(Etablissement.departement, Etablissement.nom, Classe.niveau)
        .all()
    )
    sorties = [_sortie(db, classe, etab, classe.id in mes_classes) for classe, etab in lignes]
    return sorted(sorties, key=lambda s: not s.inscrit)


@router.post(
    "/alphabetisation/inscriptions", response_model=ClasseAlphabetisationOut, status_code=status.HTTP_201_CREATED
)
def s_inscrire(
    payload: InscriptionAlphabetisationIn,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> ClasseAlphabetisationOut:
    """Inscription directe (adulte, gratuite) dans la limite des places."""
    classe = db.get(Classe, payload.classe_id)
    etab = db.get(Etablissement, classe.etablissement_id) if classe else None
    if classe is None or etab is None or etab.type != TypeEtablissement.CA or not etab.actif:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe d'alphabétisation introuvable.")
    if _nombre_inscrits(db, classe.id) >= classe.capacite:
        raise api_error(
            status.HTTP_409_CONFLICT, "classe_complete", "Cette classe est complète. Choisissez un autre centre ou revenez plus tard."
        )
    db.add(InscriptionAlphabetisation(utilisateur_id=utilisateur.id, classe_id=classe.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "deja_inscrit", "Vous êtes déjà inscrit dans cette classe.") from None
    return _sortie(db, classe, etab, True)


@router.get("/etablissements/{etablissement_id}/apprenants-adultes", response_model=list[ApprenantOut])
def apprenants_du_centre(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[ApprenantOut]:
    verifier_portee_etablissement(db, admin, etablissement_id)
    lignes = (
        db.query(InscriptionAlphabetisation, Utilisateur, Classe)
        .join(Utilisateur, Utilisateur.id == InscriptionAlphabetisation.utilisateur_id)
        .join(Classe, Classe.id == InscriptionAlphabetisation.classe_id)
        .filter(Classe.etablissement_id == etablissement_id)
        .order_by(Classe.niveau, Utilisateur.nom)
        .all()
    )
    return [
        ApprenantOut(
            utilisateur_id=u.id, nom=u.nom, prenom=u.prenom, telephone=u.telephone,
            classe_id=c.id, niveau=c.niveau, inscrit_le=i.created_at,
        )
        for i, u, c in lignes
    ]
