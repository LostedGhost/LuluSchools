"""Erreurs de validation (422) en francais lisible par l'utilisateur final.

Pydantic renvoie des erreurs techniques (« String should have at least 8 characters »,
emplacement `body.mot_de_passe`). L'interface affiche le `message` de l'erreur tel quel :
on le construit donc en francais a partir de la premiere erreur, avec le nom du champ tel
qu'il apparait dans les formulaires. Le detail technique reste dans `details.fields`.
"""

from __future__ import annotations

LIBELLES_CHAMPS = {
    "email": "adresse e-mail", "identifiant": "identifiant", "mot_de_passe": "mot de passe",
    "password": "mot de passe", "ancien_mot_de_passe": "ancien mot de passe",
    "nouveau_mot_de_passe": "nouveau mot de passe", "nom": "nom", "prenom": "prénom",
    "telephone": "téléphone", "numero_mobile_money": "numéro Mobile Money", "date_naissance": "date de naissance",
    "titre": "titre", "description": "description", "motif": "motif", "matiere": "matière",
    "niveau": "niveau", "filiere": "filière", "capacite": "capacité", "prix": "prix", "montant": "montant",
    "prix_fcfa": "prix", "montant_fcfa": "montant", "date": "date", "date_debut": "date de début",
    "date_fin": "date de fin", "date_limite": "date limite", "contenu": "contenu", "texte": "texte",
    "message": "message", "question": "question", "enonce": "énoncé", "bareme_reponse": "barème",
    "points_max": "points", "note": "note", "code": "code", "ville": "ville", "adresse": "adresse",
    "syllabus": "syllabus", "lieu": "lieu", "places": "nombre de places", "quantite": "quantité",
    "reference_paiement": "référence du paiement", "reference_evaluation": "devoir concerné",
    "commentaire": "commentaire", "seuil_validation_fcfa": "seuil de validation",
}

_TYPES = {
    "missing": "est obligatoire",
    "string_too_short": "est trop court",
    "string_too_long": "est trop long",
    "too_short": "ne contient pas assez d'éléments",
    "too_long": "contient trop d'éléments",
    "greater_than": "est trop petit",
    "greater_than_equal": "est trop petit",
    "less_than": "est trop grand",
    "less_than_equal": "est trop grand",
    "int_parsing": "doit être un nombre entier",
    "float_parsing": "doit être un nombre",
    "decimal_parsing": "doit être un nombre",
    "date_parsing": "n'est pas une date valide",
    "date_from_datetime_parsing": "n'est pas une date valide",
    "datetime_parsing": "n'est pas une date et heure valides",
    "value_error.email": "n'est pas une adresse e-mail valide",
    "enum": "n'est pas une valeur autorisée",
    "literal_error": "n'est pas une valeur autorisée",
    "uuid_parsing": "n'est pas un identifiant valide",
    "bool_parsing": "doit être oui ou non",
    "json_invalid": "n'est pas lisible",
}


def _libelle(loc: tuple) -> str | None:
    noms = [str(p) for p in loc if isinstance(p, str) and p not in ("body", "query", "path", "form")]
    if not noms:
        return None
    nom = noms[-1]
    return LIBELLES_CHAMPS.get(nom, nom.replace("_", " "))


def message_validation(erreurs: list[dict]) -> str:
    if not erreurs:
        return "Certaines informations saisies sont invalides."
    e = erreurs[0]
    type_erreur = e.get("type", "")
    msg = str(e.get("msg", ""))
    # Validateurs metier (ValueError levee dans un schema) : le message est deja redige.
    if type_erreur == "value_error" and msg.startswith("Value error, "):
        texte = msg.removeprefix("Value error, ")
        return texte if texte.endswith((".", "!", "?")) else texte + "."
    if type_erreur == "value_error" and "email" in msg.lower():
        type_erreur = "value_error.email"
    champ = _libelle(tuple(e.get("loc", ())))
    raison = _TYPES.get(type_erreur, "est invalide")
    if champ is None:
        return "Certaines informations saisies sont invalides."
    suite = f" ({len(erreurs) - 1} autre(s) champ(s) à corriger)" if len(erreurs) > 1 else ""
    return f"Le champ « {champ} » {raison}{suite}."
