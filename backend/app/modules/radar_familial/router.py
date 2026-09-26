from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.core.llm import DigestFamilleError, FreeLLMClient, get_llm_client
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve
from app.modules.radar_familial.schemas import RadarFamilialOut
from app.modules.radar_familial.service import construire_sources_radar_familial

router = APIRouter(tags=["radar-familial"])


def _verifier_tuteur_de_l_eleve(db: Session, tuteur: Utilisateur, eleve_utilisateur_id: str) -> Eleve:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None or eleve.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte tuteur.")
    return eleve


@router.get("/mes-enfants/{eleve_utilisateur_id}/radar-familial", response_model=RadarFamilialOut)
def obtenir_radar_familial(
    eleve_utilisateur_id: str,
    debut: date | None = Query(default=None),
    fin: date | None = Query(default=None),
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> dict:
    """UC-36.1 : digest hebdomadaire genere a la demande (pas d'envoi pousse dans ce
    lot), par defaut sur les 7 derniers jours. UC-36.2 : le resume cite les faits fournis
    par construire_sources_radar_familial, jamais une affirmation non tracable."""
    eleve = _verifier_tuteur_de_l_eleve(db, utilisateur, eleve_utilisateur_id)
    fin = fin or date.today()
    debut = debut or (fin - timedelta(days=7))

    sources = construire_sources_radar_familial(db, eleve_utilisateur_id, debut=debut, fin=fin)
    if not sources:
        resume = "Aucun element notable n'a ete enregistre sur cette periode."
    else:
        try:
            resume = llm_client.generer_digest_famille(f"{eleve.prenom} {eleve.nom}", sources)
        except DigestFamilleError as exc:
            raise api_error(
                status.HTTP_502_BAD_GATEWAY, "reponse_echouee", "Impossible de generer le digest, veuillez reessayer."
            ) from exc

    return {
        "eleve_utilisateur_id": eleve_utilisateur_id,
        "periode_debut": debut,
        "periode_fin": fin,
        "resume": resume,
        "sources": sources,
    }
