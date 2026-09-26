import pymupdf as fitz

LARGEUR_PAGE = 595.0  # A4 portrait, en points
HAUTEUR_PAGE = 842.0
MARGE = 50.0


def _nouvelle_page(document: "fitz.Document") -> tuple["fitz.Page", float]:
    page = document.new_page(width=LARGEUR_PAGE, height=HAUTEUR_PAGE)
    return page, MARGE


def _ecrire_ligne(page: "fitz.Page", y: float, texte: str, *, taille: float = 11.0, gras: bool = False) -> float:
    if y > HAUTEUR_PAGE - MARGE:
        return y
    police = "hebo" if gras else "helv"
    page.insert_text((MARGE, y), texte, fontsize=taille, fontname=police)
    return y + taille * 1.6


def generer_pdf_passeport(passeport: dict) -> bytes:
    """UC-38.2 : export PDF du passeport, reutilise PyMuPDF (deja en place pour le rendu
    du tableau collaboratif, voir cours_direct/rendu_tableau.py) plutot que d'introduire
    une dependance PDF supplementaire jamais exercee dans ce projet."""
    document = fitz.open()
    page, y = _nouvelle_page(document)

    y = _ecrire_ligne(page, y, "Passeport de competences", taille=18, gras=True)
    y = _ecrire_ligne(page, y, f"{passeport['eleve_prenom']} {passeport['eleve_nom']}", taille=13)
    y += 10

    y = _ecrire_ligne(page, y, "Moyennes par matiere", taille=14, gras=True)
    if not passeport["moyennes_par_matiere"]:
        y = _ecrire_ligne(page, y, "Aucune moyenne disponible pour le moment.")
    for moyenne in passeport["moyennes_par_matiere"]:
        y = _ecrire_ligne(page, y, f"- {moyenne['matiere']} : {moyenne['moyenne']:.1f}/100")
    y += 10

    y = _ecrire_ligne(page, y, "Quiz reussis", taille=14, gras=True)
    if not passeport["quiz_reussis"]:
        y = _ecrire_ligne(page, y, "Aucun quiz reussi pour le moment.")
    for quiz in passeport["quiz_reussis"]:
        date_str = quiz["date"].date().isoformat() if hasattr(quiz["date"], "date") else str(quiz["date"])
        y = _ecrire_ligne(page, y, f"- {quiz['cours_titre']} ({quiz['cours_chapitre']}) : {quiz['score']:.0f}% le {date_str}")
        if y > HAUTEUR_PAGE - MARGE:
            page, y = _nouvelle_page(document)
    y += 10

    y = _ecrire_ligne(page, y, "Cours suivis", taille=14, gras=True)
    if not passeport["cours_suivis"]:
        y = _ecrire_ligne(page, y, "Aucun cours enregistre pour le moment.")
    for cours in passeport["cours_suivis"]:
        y = _ecrire_ligne(page, y, f"- {cours['titre']} ({cours['chapitre']})")
        if y > HAUTEUR_PAGE - MARGE:
            page, y = _nouvelle_page(document)
    y += 10

    y = _ecrire_ligne(page, y, "Badges", taille=14, gras=True)
    if not passeport["badges"]:
        y = _ecrire_ligne(page, y, "Aucun badge debloque pour le moment.")
    for badge in passeport["badges"]:
        y = _ecrire_ligne(page, y, f"- {badge['label']}")

    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes
