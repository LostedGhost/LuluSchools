"""Lot 7.2 : preferences d'accessibilite synchronisees et lecture a voix haute pour tous.

La lecture a voix haute passe d'abord par la voix du navigateur (gratuite, hors ligne) ;
cette route n'est que le repli quand le telephone n'a pas de voix francaise installee -
cas frequent sur les Android d'entree de gamme."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, get_current_active_user
from app.core.llm import FreeLLMClient, SyntheseVocaleError, get_llm_client
from app.core.rate_limit import consommer
from app.modules.accessibilite.schemas import PreferencesAccessibilite, SyntheseVocaleRequest
from app.modules.identite.models import Utilisateur

router = APIRouter(tags=["accessibilite"])

_LECTURES_PAR_HEURE = 60


@router.get("/me/preferences-accessibilite", response_model=PreferencesAccessibilite)
def mes_preferences(utilisateur: Utilisateur = Depends(get_current_active_user)) -> PreferencesAccessibilite:
    return PreferencesAccessibilite.model_validate(utilisateur.preferences_accessibilite or {})


@router.put("/me/preferences-accessibilite", response_model=PreferencesAccessibilite)
def enregistrer_mes_preferences(
    payload: PreferencesAccessibilite,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> PreferencesAccessibilite:
    utilisateur.preferences_accessibilite = payload.model_dump()
    db.commit()
    return payload


@router.post("/accessibilite/synthese-vocale")
def lire_a_voix_haute(
    payload: SyntheseVocaleRequest,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> Response:
    consommer(db, f"accessibilite_voix:{utilisateur.id}", _LECTURES_PAR_HEURE, 3600)
    try:
        audio = llm_client.synthese_vocale(payload.texte)
    except SyntheseVocaleError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "synthese_echouee", "La lecture à voix haute est indisponible pour le moment."
        ) from exc
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "private, max-age=3600"})
