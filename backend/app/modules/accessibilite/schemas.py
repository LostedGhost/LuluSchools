"""Lot 7 (conformite PAG / challenge EduTech) : preferences d'accessibilite et lecture
a voix haute, communes a tous les roles."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PreferencesAccessibilite(BaseModel):
    """Reglages de la barre d'accessibilite. Champs fermes (Literal) : une valeur inconnue
    envoyee par un client obsolete est refusee plutot que stockee telle quelle."""

    model_config = ConfigDict(extra="forbid")

    taille: Literal["normal", "grand", "tres_grand"] = "normal"
    contraste: bool = False
    espacement: bool = False
    animations_reduites: bool = False
    # "auto" : reduit si le navigateur signale l'economie de donnees ou un reseau 2G/3G.
    donnees: Literal["auto", "reduit", "normal"] = "auto"
    # Lot 7.4 : accueil par pictogrammes lus a voix haute (personnes non alphabetisees).
    mode_ecoute: bool = False
    langue_audio: Literal["fr", "fon", "yo"] = "fr"


class SyntheseVocaleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Borne : une page entiere se lit par morceaux cote client, jamais d'un seul appel.
    texte: str = Field(min_length=1, max_length=4000)
