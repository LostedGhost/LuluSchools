"""Mise en page commune des documents officiels PDF (actes, bulletins, contrats).

En-tete aux couleurs de la plateforme avec le nom et le code de l'etablissement, titre,
blocs « libelle : valeur », tableaux simples et pied avec reference de verification.
PyMuPDF (polices de base Helvetica, jeu WinAnsi : accents francais pris en charge).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pymupdf as fitz

from app.modules.etablissements.models import Etablissement

LARGEUR, HAUTEUR = 595, 842
MARGE = 40
VERT = (0.06, 0.39, 0.25)
ENCRE = (0.1, 0.12, 0.16)
GRIS = (0.4, 0.4, 0.4)
BAS_DE_CONTENU = 700  # au-dela, nouvelle page (le pied occupe le bas)


_REMPLACEMENTS = str.maketrans({
    "—": "-", "–": "-", "‑": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...",
    "œ": "oe", "Œ": "OE", "€": "EUR", " ": " ", " ": " ",
})


def latin1(texte: str) -> str:
    """Les polices de base des PDF (Helvetica) ne couvrent que le Latin-1 : on remplace les
    caracteres typographiques courants (tirets longs, apostrophes courbes, œ...) par un
    equivalent lisible au lieu de laisser apparaitre des « ? »."""
    return texte.translate(_REMPLACEMENTS).encode("latin-1", "replace").decode("latin-1")


def nouveau_document() -> fitz.Document:
    return fitz.open()


def nouvelle_page(document: fitz.Document, etablissement: Etablissement, titre: str) -> tuple[fitz.Page, float]:
    page = document.new_page(width=LARGEUR, height=HAUTEUR)
    page.draw_rect(fitz.Rect(0, 0, LARGEUR, 70), color=None, fill=VERT)
    page.insert_text((MARGE, 44), latin1(etablissement.nom[:70]), fontsize=15, color=(1, 1, 1), fontname="hebo")
    page.insert_text((MARGE, 60), f"Code établissement : {etablissement.code_etablissement}", fontsize=9, color=(1, 1, 1))
    page.insert_textbox(fitz.Rect(MARGE, 96, LARGEUR - MARGE, 140), latin1(titre.upper()), fontsize=18, color=ENCRE, fontname="hebo", align=1)
    return page, 160


def paragraphe(page: fitz.Page, y: float, texte: str, taille: float = 11, hauteur: float | None = None) -> float:
    """Texte justifie sur la largeur utile ; renvoie l'ordonnee suivante."""
    lignes_estimees = max(1, int(len(texte) * taille * 0.5 / (LARGEUR - 2 * MARGE)) + 1 + texte.count("\n"))
    h = hauteur or lignes_estimees * taille * 1.45 + 6
    page.insert_textbox(fitz.Rect(MARGE, y, LARGEUR - MARGE, y + h), latin1(texte), fontsize=taille, color=ENCRE, align=3)
    return y + h + 6


def champs(page: fitz.Page, y: float, lignes: list[tuple[str, str]], colonne: float = 220) -> float:
    for libelle, valeur in lignes:
        page.insert_text((MARGE + 20, y), f"{libelle} :", fontsize=11, color=(0.35, 0.35, 0.35))
        page.insert_text((colonne, y), latin1(valeur[:60]), fontsize=11, color=ENCRE, fontname="hebo")
        y += 20
    return y + 10


def tableau(page: fitz.Page, y: float, entetes: list[tuple[str, float]], lignes: list[list[str]]) -> float:
    """entetes = [(libelle, abscisse)] ; les lignes suivent les memes abscisses."""
    for libelle, x in entetes:
        page.insert_text((x, y), libelle, fontsize=10, fontname="hebo", color=ENCRE)
    y += 6
    page.draw_line((MARGE, y), (LARGEUR - MARGE, y), color=(0.7, 0.7, 0.7), width=0.6)
    y += 16
    for ligne in lignes:
        for (_, x), valeur in zip(entetes, ligne):
            page.insert_text((x, y), latin1(valeur), fontsize=9.5, color=ENCRE)
        y += 16
    return y


def pied(page: fitz.Page, reference: str, mention: str = "Fait le {date}, pour servir et valoir ce que de droit.") -> None:
    aujourdhui = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    page.insert_text((MARGE, 740), latin1(mention.format(date=aujourdhui)), fontsize=10, color=ENCRE)
    page.insert_text((MARGE, 758), "Document généré par LuluSchools à partir des données officielles de l'établissement.", fontsize=8, color=GRIS)
    page.insert_text((MARGE, 770), f"Référence de vérification : {reference}", fontsize=8, color=GRIS)


def vers_octets(document: fitz.Document) -> bytes:
    contenu = document.tobytes(garbage=3, deflate=True)
    document.close()
    return contenu


def texte_long(document: fitz.Document, page: fitz.Page, y: float, texte: str, etablissement: Etablissement,
               titre_suite: str, taille: float = 10, largeur_car: int = 100) -> tuple[fitz.Page, float]:
    """Texte de longueur quelconque (syllabus...) : retour a la ligne et nouvelles pages
    automatiques. Renvoie la page courante et l'ordonnee suivante."""
    import textwrap

    for paragraphe_brut in latin1(texte).splitlines() or [""]:
        lignes = textwrap.wrap(paragraphe_brut, largeur_car) or [""]
        for ligne in lignes:
            if y > BAS_DE_CONTENU:
                page, y = nouvelle_page(document, etablissement, titre_suite)
            page.insert_text((MARGE, y), ligne, fontsize=taille, color=ENCRE)
            y += taille * 1.5
    return page, y + 6
