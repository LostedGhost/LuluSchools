"""Bulletin de notes en PDF (une periode) : identite, moyennes par matiere avec
coefficients, moyenne generale ponderee, decision du conseil de classe."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import pdf_officiel as pdf
from app.modules.etablissements.models import Classe, Etablissement
from app.modules.evaluations import periodes
from app.modules.evaluations.decisions import libelle_decision
from app.modules.evaluations.models import Bulletin
from app.modules.inscriptions.models import Eleve


def generer_pdf_bulletin(
    db: Session, eleve: Eleve, classe: Classe, bulletin: Bulletin, matieres: list[tuple[str, float, float, int]]
) -> bytes:
    etablissement = db.get(Etablissement, classe.etablissement_id)
    periode = periodes.trouver(etablissement.type, classe.annee_academique, bulletin.periode)
    libelle_periode = periode.libelle if periode else bulletin.periode

    document = pdf.nouveau_document()
    page, y = pdf.nouvelle_page(document, etablissement, f"Bulletin de notes — {libelle_periode}")
    y = pdf.champs(page, y, [
        ("Nom et prénom(s)", f"{eleve.nom.upper()} {eleve.prenom}"),
        ("Matricule", eleve.matricule or "—"),
        ("Classe", classe.niveau + (f" — {classe.filiere}" if classe.filiere else "")),
        ("Année académique", classe.annee_academique),
        ("Période", f"{libelle_periode}" + (f" (du {periode.debut:%d/%m/%Y} au {periode.fin:%d/%m/%Y})" if periode else "")),
    ])

    colonnes = [("Matière", pdf.MARGE), ("Coefficient", 300), ("Devoirs", 390), ("Moyenne / 100", 470)]
    lignes = [[m[:40], f"{c:g}", str(n), f"{moy:.1f}"] for m, moy, c, n in matieres]
    y = pdf.tableau(page, y, colonnes, lignes)
    if not matieres:
        page.insert_text((pdf.MARGE, y), pdf.latin1("Aucune évaluation comptabilisée pour cette période."), fontsize=10, color=pdf.GRIS)
        y += 16

    y += 14
    page.draw_rect((pdf.MARGE, y - 16, pdf.LARGEUR - pdf.MARGE, y + 12), color=None, fill=(0.93, 0.96, 0.94))
    page.insert_text((pdf.MARGE + 10, y), f"Moyenne générale pondérée : {bulletin.moyenne_generale:.1f} / 100",
                     fontsize=12, fontname="hebo", color=pdf.ENCRE)
    y += 36
    decision = libelle_decision(bulletin.decision_passage) if bulletin.valide_par_conseil else None
    page.insert_text((pdf.MARGE, y), pdf.latin1("Décision du conseil de classe :"), fontsize=11, color=(0.35, 0.35, 0.35))
    page.insert_text((230, y), pdf.latin1(decision or "en attente de délibération"), fontsize=11, fontname="hebo" if decision else "helv",
                     color=pdf.ENCRE if decision else pdf.GRIS)

    pdf.pied(page, bulletin.id, mention="Édité le {date}. Moyennes sur 100, devoirs sommatifs de la période uniquement.")
    return pdf.vers_octets(document)
