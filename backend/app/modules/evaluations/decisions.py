"""Decisions du conseil de classe (POST /bulletins/{id}/valider-passage).

[Delegue] Codes proposes par l'interface ; le champ reste libre cote API (compatibilite).
Une decision « favorable » (admis) ouvre droit au certificat de reussite genere
automatiquement (actes/generation.py).
"""

from __future__ import annotations

DECISIONS = {
    "admis": "Admis(e) en classe supérieure",
    "admis_annee_validee": "Année validée",
    "redouble": "Autorisé(e) à redoubler",
    "reoriente": "Réorienté(e)",
}
# Anciennes valeurs libres encore presentes en base.
_FAVORABLES_HISTORIQUES = {"passage", "passage_classe_superieure"}


def libelle_decision(code: str | None) -> str | None:
    if not code:
        return None
    return DECISIONS.get(code, code.replace("_", " ").capitalize())


def est_favorable(code: str | None) -> bool:
    return bool(code) and (code.startswith("admis") or code in _FAVORABLES_HISTORIQUES)
