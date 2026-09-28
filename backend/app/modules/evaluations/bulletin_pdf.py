"""Bulletin de notes en PDF (une periode) : identite, puis pour chaque matiere son
coefficient, sa moyenne et le DETAIL de ses evaluations (date, intitule, note obtenue sur
son bareme), moyenne generale ponderee et decision du conseil de classe."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core import pdf_officiel as pdf
from app.modules.etablissements.models import Classe, Etablissement
from app.modules.evaluations import periodes
from app.modules.evaluations.decisions import libelle_decision
from app.modules.evaluations.models import Bulletin
from app.modules.inscriptions.models import Eleve

if TYPE_CHECKING:
    from app.modules.evaluations.router import NoteDuBulletin

FOND_MATIERE = (0.93, 0.96, 0.94)
X_DATE, X_INTITULE, X_NOTE, X_SUR_100 = pdf.MARGE + 10, pdf.MARGE + 80, 400, 480


def _nombre(v: float) -> str:
    return f"{v:g}".replace(".", ",")


def generer_pdf_bulletin(
    db: Session, eleve: Eleve, classe: Classe, bulletin: Bulletin,
    matieres: list[tuple[str, float, float, int]], evaluations: list["NoteDuBulletin"] | None = None,
) -> bytes:
    etablissement = db.get(Etablissement, classe.etablissement_id)
    periode = periodes.trouver(etablissement.type, classe.annee_academique, bulletin.periode)
    libelle_periode = periode.libelle if periode else bulletin.periode
    titre = f"Bulletin de notes - {libelle_periode}"

    document = pdf.nouveau_document()
    page, y = pdf.nouvelle_page(document, etablissement, titre)
    y = pdf.champs(page, y, [
        ("Nom et prénom(s)", f"{eleve.nom.upper()} {eleve.prenom}"),
        ("Matricule", eleve.matricule or "-"),
        ("Classe", classe.niveau + (f" - {classe.filiere}" if classe.filiere else "")),
        ("Année académique", classe.annee_academique),
        ("Période", f"{libelle_periode}" + (f" (du {periode.debut:%d/%m/%Y} au {periode.fin:%d/%m/%Y})" if periode else "")),
    ])

    def place(hauteur: float) -> None:
        nonlocal page, y
        if y + hauteur > pdf.BAS_DE_CONTENU:
            page, y = pdf.nouvelle_page(document, etablissement, f"{titre} (suite)")

    # En-tete des colonnes du detail
    for libelle, x in (("Date", X_DATE), ("Évaluation", X_INTITULE), ("Note obtenue", X_NOTE), ("Sur 100", X_SUR_100)):
        page.insert_text((x, y), pdf.latin1(libelle), fontsize=9, fontname="hebo", color=pdf.GRIS)
    y += 12

    par_matiere: dict[str, list] = {}
    for n in evaluations or []:
        par_matiere.setdefault(n.devoir.matiere, []).append(n)

    for matiere, moyenne, coefficient, nombre in matieres:
        place(26 + 15 * min(len(par_matiere.get(matiere, [])), 3))
        page.draw_rect((pdf.MARGE, y - 2, pdf.LARGEUR - pdf.MARGE, y + 18), color=None, fill=FOND_MATIERE)
        page.insert_text((pdf.MARGE + 6, y + 12), pdf.latin1(matiere[:45]), fontsize=10.5, fontname="hebo", color=pdf.ENCRE)
        page.insert_text((300, y + 12), f"coef. {_nombre(coefficient)}", fontsize=9.5, color=pdf.ENCRE)
        page.insert_text((X_SUR_100 - 42, y + 12), pdf.latin1(f"Moyenne : {moyenne:.1f}"), fontsize=10, fontname="hebo", color=pdf.ENCRE)
        y += 32
        for n in par_matiere.get(matiere, []):
            place(15)
            page.insert_text((X_DATE, y), f"{n.devoir.date_limite:%d/%m/%Y}", fontsize=9, color=pdf.ENCRE)
            page.insert_text((X_INTITULE, y), pdf.latin1(n.devoir.titre[:58]), fontsize=9, color=pdf.ENCRE)
            if n.note is None:
                page.insert_text((X_NOTE, y), pdf.latin1("non rendu (0)"), fontsize=9, color=(0.7, 0.2, 0.2))
            else:
                page.insert_text((X_NOTE, y), f"{_nombre(round(n.note, 2))} / {_nombre(n.total)}", fontsize=9, fontname="hebo", color=pdf.ENCRE)
            page.insert_text((X_SUR_100, y), f"{n.sur_100:.1f}", fontsize=9, color=pdf.ENCRE)
            y += 15
        y += 6

    if not matieres:
        page.insert_text((pdf.MARGE, y + 6), pdf.latin1("Aucune évaluation comptabilisée pour cette période."), fontsize=10, color=pdf.GRIS)
        y += 22

    place(60)
    y += 16
    page.draw_rect((pdf.MARGE, y - 16, pdf.LARGEUR - pdf.MARGE, y + 12), color=None, fill=FOND_MATIERE)
    page.insert_text((pdf.MARGE + 10, y), pdf.latin1(f"Moyenne générale pondérée : {bulletin.moyenne_generale:.1f} / 100"),
                     fontsize=12, fontname="hebo", color=pdf.ENCRE)
    y += 34
    decision = libelle_decision(bulletin.decision_passage) if bulletin.valide_par_conseil else None
    page.insert_text((pdf.MARGE, y), pdf.latin1("Décision du conseil de classe :"), fontsize=11, color=(0.35, 0.35, 0.35))
    page.insert_text((230, y), pdf.latin1(decision or "en attente de délibération"), fontsize=11, fontname="hebo" if decision else "helv",
                     color=pdf.ENCRE if decision else pdf.GRIS)

    mention = "Édité le {date}. Devoirs sommatifs de la période ; copie non rendue après l'échéance : 0."
    for p in document:
        pdf.pied(p, bulletin.id, mention=mention)
    return pdf.vers_octets(document)
