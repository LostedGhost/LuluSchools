import pymupdf as fitz

from app.modules.cours_direct.models import TraitTableau, TypeTraitTableau

LARGEUR_TABLEAU = 1000.0
HAUTEUR_TABLEAU = 600.0
COULEUR_FOND = (0.06, 0.2, 0.13)  # vert tableau noir, plutot qu'un blanc de canvas generique
COULEUR_PAR_DEFAUT = (1.0, 1.0, 1.0)  # "craie blanche"


def _couleur(hexadecimal: str | None) -> tuple[float, float, float]:
    if not hexadecimal or not hexadecimal.startswith("#") or len(hexadecimal) != 7:
        return COULEUR_PAR_DEFAUT
    try:
        r = int(hexadecimal[1:3], 16) / 255
        g = int(hexadecimal[3:5], 16) / 255
        b = int(hexadecimal[5:7], 16) / 255
        return (r, g, b)
    except ValueError:
        return COULEUR_PAR_DEFAUT


def rendre_panneau_png(traits: list[TraitTableau]) -> bytes:
    """UC-25.6 : rejoue les traits d'un panneau dans l'ordre (un EFFACEMENT vide tout ce
    qui precede - meme logique que le rejeu 'time-lapse' cote client) et rasterise le
    resultat final en PNG. Un trait individuel malforme (donnees clients) est ignore
    plutot que de faire echouer toute la capture."""
    visibles: list[TraitTableau] = []
    for trait in sorted(traits, key=lambda t: t.created_at):
        if trait.type == TypeTraitTableau.EFFACEMENT:
            visibles = []
        else:
            visibles.append(trait)

    document = fitz.open()
    page = document.new_page(width=LARGEUR_TABLEAU, height=HAUTEUR_TABLEAU)
    page.draw_rect(page.rect, color=None, fill=COULEUR_FOND)

    for trait in visibles:
        try:
            _dessiner_trait(page, trait)
        except (KeyError, TypeError, ValueError):
            continue

    pixmap = page.get_pixmap()
    png_bytes = pixmap.tobytes("png")
    document.close()
    return png_bytes


def _dessiner_trait(page: "fitz.Page", trait: TraitTableau) -> None:
    donnees = trait.donnees or {}
    couleur = _couleur(donnees.get("couleur"))

    if trait.type == TypeTraitTableau.TRAIT_LIBRE:
        points = donnees.get("points") or []
        if len(points) < 2:
            return
        points_mis_a_l_echelle = [
            fitz.Point(float(x) * LARGEUR_TABLEAU, float(y) * HAUTEUR_TABLEAU) for x, y in points
        ]
        epaisseur = max(1.0, float(donnees.get("epaisseur", 0.01)) * min(LARGEUR_TABLEAU, HAUTEUR_TABLEAU))
        page.draw_polyline(points_mis_a_l_echelle, color=couleur, width=epaisseur)
    elif trait.type == TypeTraitTableau.TEXTE:
        texte = str(donnees.get("texte", ""))
        if not texte:
            return
        x = float(donnees.get("x", 0.0)) * LARGEUR_TABLEAU
        y = float(donnees.get("y", 0.0)) * HAUTEUR_TABLEAU
        taille = max(6.0, float(donnees.get("taille", 0.03)) * HAUTEUR_TABLEAU)
        page.insert_text((x, y), texte, fontsize=taille, color=couleur)
