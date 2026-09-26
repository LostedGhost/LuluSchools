import pymupdf as fitz


def convertir_en_image(contenu: bytes, content_type: str) -> tuple[bytes, str]:
    """FreeLLM n'accepte que des images en vision (voir ADR-002) : convertit la premiere
    page d'un PDF en PNG. Les autres types sont supposes deja etre des images (jpg/png).
    Partage entre modules (recrutement, evaluations) - vivait a l'origine dans
    recrutement/conversion.py avant que evaluations en ait besoin aussi (UC-26)."""
    if content_type == "application/pdf":
        document = fitz.open(stream=contenu, filetype="pdf")
        try:
            page = document.load_page(0)
            pixmap = page.get_pixmap()
            return pixmap.tobytes("png"), "image/png"
        finally:
            document.close()
    return contenu, content_type
