import base64
import io

import httpx
import pymupdf as fitz

# FreeLLM (voir ADR-002 et son code source, server/src/lib/content.ts) ne transmet aux
# modeles que le texte et les images : un bloc PDF ou audio serait ignore sans erreur. Un
# PDF est donc lu ici (texte, ou pages rendues en images s'il est scanne) avant l'appel.

TYPES_IMAGE = frozenset({"image/jpeg", "image/png", "image/webp"})
TYPE_PDF = "application/pdf"
TYPES_PIECE_JOINTE = TYPES_IMAGE | {TYPE_PDF}

MAX_CARACTERES_DOCUMENT = 40_000
# En dessous, un PDF est considere comme scanne (pages-images sans couche texte).
_SEUIL_TEXTE_SIGNIFICATIF = 200
MAX_PAGES_EN_IMAGES = 3


class DocumentIllisibleError(Exception):
    """PDF corrompu, chiffre ou vide."""


def extraire_texte_pdf(contenu: bytes, max_caracteres: int = MAX_CARACTERES_DOCUMENT) -> str:
    try:
        document = fitz.open(stream=contenu, filetype="pdf")
    except Exception as exc:  # pymupdf leve des types varies selon la corruption
        raise DocumentIllisibleError("PDF illisible.") from exc
    try:
        if document.needs_pass:
            raise DocumentIllisibleError("PDF protege par mot de passe.")
        morceaux: list[str] = []
        total = 0
        for page in document:
            texte = page.get_text().strip()
            if not texte:
                continue
            morceaux.append(texte)
            total += len(texte)
            if total >= max_caracteres:
                break
        return "\n\n".join(morceaux)[:max_caracteres]
    finally:
        document.close()


def pages_pdf_en_images(contenu: bytes, max_pages: int = MAX_PAGES_EN_IMAGES) -> list[bytes]:
    """Pour un PDF scanne : ses premieres pages en PNG, lisibles par un modele vision."""
    try:
        document = fitz.open(stream=contenu, filetype="pdf")
    except Exception as exc:
        raise DocumentIllisibleError("PDF illisible.") from exc
    try:
        images = []
        for index in range(min(max_pages, document.page_count)):
            pixmap = document.load_page(index).get_pixmap(dpi=110)
            images.append(pixmap.tobytes("png"))
        return images
    finally:
        document.close()


def texte_pdf_significatif(texte: str) -> bool:
    return len(texte.strip()) >= _SEUIL_TEXTE_SIGNIFICATIF


def url_data_image(contenu: bytes, content_type: str) -> str:
    return f"data:{content_type};base64,{base64.b64encode(contenu).decode()}"


def telecharger_borne(url: str, max_octets: int) -> bytes:
    """Telecharge un fichier (lien signe LuluFiles) sans jamais depasser max_octets."""
    tampon = io.BytesIO()
    with httpx.stream("GET", url, timeout=httpx.Timeout(30.0), follow_redirects=True) as reponse:
        reponse.raise_for_status()
        for bloc in reponse.iter_bytes():
            tampon.write(bloc)
            if tampon.tell() > max_octets:
                raise DocumentIllisibleError("Document trop volumineux.")
    return tampon.getvalue()
