import json

from fastapi import status

from app.core.deps import api_error


def valider_reponses_formulaire(schema_formulaire: list[dict] | None, reponses_json: str | dict | None) -> dict | None:
    """UC-47/50/62/64 (lot admin etablissement) : point d'entree UNIQUE de validation des
    reponses a un formulaire dynamique - reutilise par recrutement (Candidature) et actes
    (DemandeActeAcademique), un seul moteur pour les deux usages. `reponses_json` est une
    chaine JSON (Form multipart) representant {champ_id: valeur} ; pour un champ de type
    "fichier", la valeur attendue est deja un lulufiles_file_id (upload fait par
    l'appelant avant cet appel, jamais ici)."""
    if not schema_formulaire:
        return None
    if not reponses_json:
        champs_requis = [c["id"] for c in schema_formulaire if c.get("requis")]
        if champs_requis:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "reponses_formulaire_requises",
                f"Champ(s) requis manquant(s) : {', '.join(champs_requis)}.",
            )
        return None

    if isinstance(reponses_json, dict):
        reponses = reponses_json
    else:
        try:
            reponses = json.loads(reponses_json)
        except (ValueError, TypeError) as exc:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "reponses_formulaire_invalides", "Le formulaire envoyé est illisible, veuillez réessayer."
            ) from exc
    if not isinstance(reponses, dict):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "reponses_formulaire_invalides", "Le formulaire envoyé est illisible, veuillez réessayer."
        )

    champs_par_id = {c["id"]: c for c in schema_formulaire}
    inconnus = set(reponses.keys()) - set(champs_par_id.keys())
    if inconnus:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "champ_inconnu",
            f"Champ(s) hors du formulaire : {', '.join(sorted(inconnus))}.",
        )

    for champ in schema_formulaire:
        valeur = reponses.get(champ["id"])
        # Un champ "fichier" requis n'est jamais bloquant a ce stade : le fichier arrive
        # par un appel dedie APRES la creation (voir POST /demandes-actes/{id}/pieces/
        # {champ_id}) - le bloquer ici interdirait de creer la demande avant d'avoir
        # deja l'id de la demande necessaire a cet upload.
        if champ.get("requis") and champ["type"] != "fichier" and (valeur is None or valeur == ""):
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "reponses_formulaire_requises", f"Champ requis manquant : {champ['id']}."
            )
        if valeur is None:
            continue
        if champ["type"] == "choix_unique" and champ.get("options") and valeur not in champ["options"]:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "option_invalide", f"Valeur hors options pour {champ['id']}.")
        if champ["type"] == "choix_multiple" and champ.get("options"):
            valeurs = valeur if isinstance(valeur, list) else [valeur]
            if any(v not in champ["options"] for v in valeurs):
                raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "option_invalide", f"Valeur hors options pour {champ['id']}.")

    return reponses
