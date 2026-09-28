"""Lot 7.4 — mode Ecoute : GET /ecoute/tuteur (phrases a lire a voix haute)."""

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.modules.ecoute.service import resume_oral_tuteur
from app.modules.identite.models import RoleUtilisateur, Utilisateur

router = APIRouter(tags=["ecoute"])


class TuileOut(BaseModel):
    cle: str
    titre: str
    phrase: str
    lien: str
    alerte: bool
    consentement_inscription_id: str | None = None


class EnfantEcouteOut(BaseModel):
    eleve_utilisateur_id: str | None
    prenom: str
    tuiles: list[TuileOut]


class EcouteTuteurOut(BaseModel):
    accueil: str
    enfants: list[EnfantEcouteOut]


@router.get("/ecoute/tuteur", response_model=EcouteTuteurOut)
def ecoute_tuteur(
    db: Session = Depends(get_db), tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR))
) -> EcouteTuteurOut:
    enfants = resume_oral_tuteur(db, tuteur.id)
    if enfants:
        accueil = (
            f"Bonjour {tuteur.prenom}. Touchez une image pour écouter les nouvelles de "
            f"{', '.join(e.prenom for e in enfants)}."
        )
    else:
        accueil = f"Bonjour {tuteur.prenom}. Vous n'avez encore inscrit aucun enfant. Touchez l'image « Inscrire » pour commencer."
    return EcouteTuteurOut(accueil=accueil, enfants=[EnfantEcouteOut(**asdict(e)) for e in enfants])
