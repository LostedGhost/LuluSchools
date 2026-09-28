"""Contrat d'enseignement en PDF : parties, poste, duree, syllabus et bloc de signature.

Signe : image du trace de signature, horodatage et empreinte SHA-256 du syllabus au moment
de la signature (piste d'audit, ADR-004 ; signature electronique simple, Art. 284-285).
Non signe : le meme document marque « En attente de signature », pour relecture avant signature.
"""

from __future__ import annotations

import logging

import httpx
import pymupdf as fitz
from sqlalchemy.orm import Session

from app.core import pdf_officiel as pdf
from app.core.documents import DocumentIllisibleError, telecharger_borne
from app.core.files import FileStorageError, LuluFilesClient
from app.modules.etablissements.models import Etablissement
from app.modules.identite.models import Utilisateur
from app.modules.recrutement.models import Candidature, Contrat, Poste, StatutContrat

logger = logging.getLogger(__name__)

MAX_SIGNATURE_OCTETS = 2 * 1024 * 1024


def _image_signature(files_client: LuluFilesClient, file_id: str) -> bytes | None:
    try:
        return telecharger_borne(files_client.get_signed_link(file_id), MAX_SIGNATURE_OCTETS)
    except (FileStorageError, DocumentIllisibleError, httpx.HTTPError):
        logger.warning("contrat: image de signature %s indisponible - PDF sans l'image.", file_id)
        return None


def generer_pdf_contrat(db: Session, contrat: Contrat, files_client: LuluFilesClient) -> bytes:
    etablissement = db.get(Etablissement, contrat.etablissement_id)
    enseignant = db.get(Utilisateur, contrat.enseignant_id)
    candidature = db.get(Candidature, contrat.candidature_id)
    poste = db.get(Poste, candidature.poste_id) if candidature else None
    signe = contrat.statut == StatutContrat.SIGNE

    document = pdf.nouveau_document()
    titre = "Contrat d'enseignement"
    page, y = pdf.nouvelle_page(document, etablissement, titre)
    if not signe:
        page.insert_textbox(fitz.Rect(pdf.MARGE, 132, pdf.LARGEUR - pdf.MARGE, 150), "EN ATTENTE DE SIGNATURE",
                            fontsize=10, color=(0.75, 0.2, 0.2), fontname="hebo", align=1)

    y = pdf.champs(page, y, [
        ("Établissement", etablissement.nom),
        ("Enseignant", f"{enseignant.prenom} {enseignant.nom.upper()}"),
        ("Contact", enseignant.email or enseignant.telephone or "—"),
        ("Poste", (poste.titre if poste else "—") + (f" ({poste.matiere})" if poste and poste.matiere else "")),
        ("Établi le", f"{contrat.created_at:%d/%m/%Y}"),
        ("Échéance", f"{contrat.date_fin:%d/%m/%Y}"),
    ], colonne=200)

    page.insert_text((pdf.MARGE, y), pdf.latin1("Syllabus et engagements"), fontsize=12, fontname="hebo", color=pdf.ENCRE)
    page, y = pdf.texte_long(document, page, y + 20, contrat.syllabus, etablissement, f"{titre} (suite)")

    if y > pdf.BAS_DE_CONTENU - 150:
        page, y = pdf.nouvelle_page(document, etablissement, f"{titre} (suite)")
    y += 10
    page.insert_text((pdf.MARGE, y), pdf.latin1("Signature de l'enseignant"), fontsize=12, fontname="hebo", color=pdf.ENCRE)
    y += 12
    if signe:
        image = _image_signature(files_client, contrat.signature_image_lulufiles_id) if contrat.signature_image_lulufiles_id else None
        if not image:
            page.insert_text((pdf.MARGE, y + 40), "(image du tracé de signature momentanément indisponible)", fontsize=9, color=pdf.GRIS)
        if image:
            try:
                page.insert_image(fitz.Rect(pdf.MARGE, y, pdf.MARGE + 200, y + 80), stream=image, keep_proportion=True)
            except (RuntimeError, ValueError):
                logger.warning("contrat: image de signature illisible pour le contrat %s.", contrat.id)
        y += 92
        page.insert_text((pdf.MARGE, y), f"Signé électroniquement le {contrat.signature_horodatage:%d/%m/%Y à %H:%M} (UTC).",
                         fontsize=10, color=pdf.ENCRE)
        y += 14
        page.insert_text((pdf.MARGE, y), f"Empreinte SHA-256 du syllabus signé : {contrat.signature_hash_document}",
                         fontsize=7.5, color=pdf.GRIS)
        y += 12
        page.insert_text((pdf.MARGE, y), pdf.latin1("Signature électronique simple (loi n° 2017-20, art. 284 et 285)."), fontsize=7.5, color=pdf.GRIS)
    else:
        page.draw_rect(fitz.Rect(pdf.MARGE, y, pdf.MARGE + 240, y + 80), color=(0.7, 0.7, 0.7), width=0.8, dashes="[3] 0")
        page.insert_text((pdf.MARGE + 10, y + 44), pdf.latin1("À signer depuis l'espace enseignant"), fontsize=9, color=pdf.GRIS)

    mention = "Édité le {date}." if not signe else "Édité le {date} : copie conforme du contrat signé."
    for p in document:
        pdf.pied(p, contrat.id, mention=mention)
    return pdf.vers_octets(document)
