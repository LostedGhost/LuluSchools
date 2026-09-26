"""Complement du mega seed (scripts/seed_mega.py) : renseigne latitude/longitude
pour des etablissements deja crees, sans y toucher directement.

Depuis que scripts/seed_mega.py fixe lui-meme latitude/longitude a la creation de
chaque etablissement (meme logique de devinette qu'ici), ce script ne sert plus
qu'a completer une base DEJA peuplee AVANT cet ajout (donc avec latitude/longitude
encore NULL), ou a recalculer les positions d'un jeu de donnees existant sans
tout re-seeder (--overwrite). A lancer APRES que les migrations 0002/0003 soient
appliquees a la base cible.

Comportement : devine une position plausible a partir du NOM de chaque
etablissement (les noms generes par seed_mega.py referencent deja de vraies
villes/quartiers beninois - Cotonou, Porto-Novo, Abomey-Calavi, Abomey, Parakou,
Godomey, Seme-Kpodji, Akpakpa - ou de vraies institutions connues comme l'UNSTIM
d'Abomey ou l'INSTI de Lokossa), avec un petit ecart deterministe par etablissement
pour eviter que plusieurs etablissements d'une meme ville se superposent
exactement sur la carte. Ne touche PAR DEFAUT que les etablissements dont
latitude/longitude sont encore NULL (idempotent, rejouable sans risque) ;
--overwrite force la mise a jour de tous les etablissements.

Usage :
    cd backend
    python scripts/update_localisations.py
    python scripts/update_localisations.py --overwrite
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main  # noqa: F401  # enregistre tous les modeles sur Base.metadata

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.etablissements.models import Etablissement

# Institutions reelles identifiables par un fragment de nom, mais dont le nom ne
# contient pas litteralement la ville (verifie avant la table de villes ci-dessous).
INSTITUTIONS_CONNUES: dict[str, tuple[float, float]] = {
    "mathieu bouké": (9.3372, 2.6303),  # Lycee Mathieu Bouke - Parakou
    "toffa 1er": (6.4969, 2.6289),  # Lycee Toffa 1er - Porto-Novo
    "technologie industrielle": (6.6389, 1.7167),  # INSTI - Lokossa
    "ingénierie et mathématiques": (7.1825, 1.9911),  # UNSTIM - Abomey
}

# Villes/quartiers beninois reels references par les noms generes par seed_mega.py.
# Ordre important : les cles les plus specifiques (ex. "abomey-calavi") doivent
# précéder les cles qu'elles contiennent (ex. "abomey"), sans quoi le match generique
# l'emporterait a tort sur le match specifique.
VILLES_BENIN: dict[str, tuple[float, float]] = {
    "abomey-calavi": (6.4025, 2.3389),
    "porto-novo": (6.4969, 2.6289),
    "seme-kpodji": (6.3661, 2.6156),
    "godomey": (6.3958, 2.3336),
    "akpakpa": (6.3644, 2.4453),
    "parakou": (9.3372, 2.6303),
    "abomey": (7.1825, 1.9911),
    "cotonou": (6.3703, 2.3912),
}


def _normaliser(texte: str) -> str:
    remplacements = {"é": "e", "è": "e", "ê": "e", "ô": "o", "à": "a", "î": "i", "’": "-", "'": "-"}
    resultat = texte.lower()
    for accentue, simple in remplacements.items():
        resultat = resultat.replace(accentue, simple)
    return resultat


def _jitter(etablissement_id: str, amplitude: float = 0.015) -> tuple[float, float]:
    """Petit ecart deterministe (~± amplitude degres, de l'ordre du km) pour ne pas
    empiler plusieurs etablissements d'une meme ville exactement au meme point."""
    digest = hashlib.sha256(etablissement_id.encode()).hexdigest()
    dx = (int(digest[:8], 16) / 0xFFFFFFFF - 0.5) * 2 * amplitude
    dy = (int(digest[8:16], 16) / 0xFFFFFFFF - 0.5) * 2 * amplitude
    return dx, dy


def deviner_coordonnees(nom: str, etablissement_id: str) -> tuple[float, float]:
    nom_normalise = _normaliser(nom)

    base: tuple[float, float] | None = None
    for fragment, coords in INSTITUTIONS_CONNUES.items():
        if _normaliser(fragment) in nom_normalise:
            base = coords
            break
    if base is None:
        for ville, coords in VILLES_BENIN.items():
            if ville in nom_normalise:
                base = coords
                break
    if base is None:
        base = VILLES_BENIN["cotonou"]  # capitale economique : repli par defaut raisonnable

    dx, dy = _jitter(etablissement_id)
    return round(base[0] + dx, 6), round(base[1] + dy, 6)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Recalcule aussi la position des etablissements qui en ont deja une (par defaut : seuls les NULL sont traites).",
    )
    parser.add_argument("--force", action="store_true", help="Ignore la verification ENVIRONMENT=development.")
    args = parser.parse_args()

    if settings.environment != "development" and not args.force:
        print(
            f"ENVIRONMENT={settings.environment!r} (pas 'development') : relancez avec --force si vous etes "
            "absolument certain de la base ciblee (voir DATABASE_URL)."
        )
        raise SystemExit(1)

    print(f"Base ciblee : {settings.database_url}")
    print(f"Environnement : {settings.environment}")

    db = SessionLocal()
    try:
        requete = db.query(Etablissement)
        if not args.overwrite:
            requete = requete.filter(Etablissement.latitude.is_(None))
        etablissements = requete.all()

        if not etablissements:
            print("Aucun etablissement a mettre a jour (tous ont deja une position - utilisez --overwrite pour forcer).")
            return

        print(f"{len(etablissements)} etablissement(s) a mettre a jour...")
        for etab in etablissements:
            lat, lng = deviner_coordonnees(etab.nom, etab.id)
            etab.latitude = lat
            etab.longitude = lng
            print(f"  {etab.code_etablissement:6s} {etab.nom[:60]:60s} -> {lat}, {lng}")

        db.commit()
        print(f"\nTermine : {len(etablissements)} etablissement(s) geolocalise(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
