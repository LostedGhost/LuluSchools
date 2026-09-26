import io

import qrcode
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

_BRAND_GREEN = "#16a34a"
_INK = "#1a2420"
_INK_SOFT = "#5b6b62"

TypeTicket = str  # "transport" | "cantine" | "evenement" - garde comme str simple, pas d'enum partage entre 3 modules


def jeton_ticket(type_ticket: TypeTicket, ticket_id: str) -> str:
    """UC-54/68 (lot admin etablissement) : le jeton encode dans le QR. Pas de signature
    HMAC (decision revisee lors du design, voir diagrammes-uml-phase-6-admin-etablissement.md) -
    l'UUID du ticket est deja cryptographiquement non devinable (128 bits aleatoires), et
    les endpoints de validation existants (valider_ticket_transport/cantine, valider_billet)
    verifient deja l'appartenance/le statut du ticket independamment de ce jeton."""
    return f"{type_ticket}:{ticket_id}"


def decoder_jeton_ticket(jeton: str) -> tuple[TypeTicket, str]:
    type_ticket, _, ticket_id = jeton.partition(":")
    if not type_ticket or not ticket_id:
        raise ValueError("Jeton de ticket invalide.")
    return type_ticket, ticket_id


def generer_pdf_ticket(titre: str, sous_titre: str, type_ticket: TypeTicket, ticket_id: str, lignes_info: list[tuple[str, str]]) -> bytes:
    """Genere un PDF minimal (format A6, taille ticket) avec un QR code encodant le jeton
    du ticket - un seul generateur partage par transport/cantine/billetterie (UC-54/68),
    pas 3 implementations dupliquees."""
    jeton = jeton_ticket(type_ticket, ticket_id)
    image_qr = qrcode.make(jeton)
    buffer_qr = io.BytesIO()
    image_qr.save(buffer_qr, format="PNG")
    buffer_qr.seek(0)

    buffer_pdf = io.BytesIO()
    pdf = canvas.Canvas(buffer_pdf, pagesize=A6)
    largeur, hauteur = A6

    pdf.setFillColor(_BRAND_GREEN)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(10 * mm, hauteur - 15 * mm, "Lulu·Schools")

    pdf.setFillColor(_INK)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(10 * mm, hauteur - 25 * mm, titre[:40])
    pdf.setFillColor(_INK_SOFT)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(10 * mm, hauteur - 31 * mm, sous_titre[:50])

    y = hauteur - 40 * mm
    pdf.setFont("Helvetica", 8)
    for label, valeur in lignes_info:
        pdf.drawString(10 * mm, y, f"{label} : {valeur}"[:55])
        y -= 5 * mm

    pdf.drawImage(ImageReader(buffer_qr), largeur - 45 * mm, 8 * mm, width=32 * mm, height=32 * mm)
    pdf.setFont("Helvetica", 6)
    pdf.drawString(10 * mm, 10 * mm, f"Reference : {ticket_id}")

    pdf.showPage()
    pdf.save()
    return buffer_pdf.getvalue()
