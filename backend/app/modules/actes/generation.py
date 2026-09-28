"""Generation et livraison AUTOMATIQUES des actes standards (UC-10, simplification A+).

Un type d'acte peut porter un `modele_document` : l'attestation de scolarite, le releve
de notes et le certificat de reussite se deduisent entierement des donnees de la plateforme
(inscription validee, devoirs corriges, bulletin, decision du conseil de classe). Le
certificat de reussite exige une decision FAVORABLE du conseil (evaluations/decisions.py) :
sans elle, la demande reste a l'A+ (jamais de certificat sans deliberation humaine). Des que la demande est payee (ou tout de suite si l'acte est
gratuit), le document est genere, televerse et la demande passe ACCEPTEE : l'A+ n'a plus
rien a faire. Au moindre echec (LuluFiles indisponible...), la demande reste EN_TRAITEMENT
et suit le circuit manuel habituel - jamais de demande perdue.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pymupdf as fitz
from sqlalchemy.orm import Session, sessionmaker

from app.core.pdf_officiel import latin1
from app.core.files import FileStorageError, LuluFilesClient
from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.etablissements.models import Classe, Etablissement
from app.modules.evaluations import periodes
from app.modules.evaluations.decisions import est_favorable, libelle_decision
from app.modules.evaluations.models import Bulletin, Devoir, NatureEvaluation, Soumission, StatutSoumission
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription

logger = logging.getLogger(__name__)

ATTESTATION_SCOLARITE = "attestation_scolarite"
RELEVE_NOTES = "releve_notes"
CERTIFICAT_REUSSITE = "certificat_reussite"
MODELES = {
    ATTESTATION_SCOLARITE: "Attestation de scolarité",
    RELEVE_NOTES: "Relevé de notes",
    CERTIFICAT_REUSSITE: "Certificat de réussite",
}

VERT = (0.06, 0.39, 0.25)
ENCRE = (0.1, 0.12, 0.16)


def _inscription_courante(db: Session, eleve: Eleve) -> Inscription | None:
    return (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )


def _entete(page, etablissement: Etablissement, titre: str) -> float:
    page.draw_rect(fitz.Rect(0, 0, 595, 70), color=None, fill=VERT)
    page.insert_text((40, 44), latin1(etablissement.nom), fontsize=15, color=(1, 1, 1), fontname="hebo")
    page.insert_text((40, 60), latin1(f"Code établissement : {etablissement.code_etablissement}"), fontsize=9, color=(1, 1, 1))
    page.insert_textbox(fitz.Rect(40, 96, 555, 140), latin1(titre.upper()), fontsize=18, color=ENCRE, fontname="hebo", align=1)
    return 160


def _pied(page, etablissement: Etablissement, demande: DemandeActeAcademique) -> None:
    aujourdhui = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    page.insert_text((40, 740), latin1(f"Fait le {aujourdhui}, pour servir et valoir ce que de droit."), fontsize=10, color=ENCRE)
    page.insert_text((40, 758), latin1("Document généré par LuluSchools à partir des données officielles de l'établissement."), fontsize=8, color=(0.4, 0.4, 0.4))
    page.insert_text((40, 770), latin1(f"Référence de vérification : {demande.id}"), fontsize=8, color=(0.4, 0.4, 0.4))


def _identite(page, y: float, eleve: Eleve, classe: Classe) -> float:
    lignes = [
        ("Nom et prénom(s)", f"{eleve.nom.upper()} {eleve.prenom}"),
        ("Date de naissance", eleve.date_naissance.strftime("%d/%m/%Y")),
        ("Matricule", eleve.matricule or "—"),
        ("Classe", f"{classe.niveau}" + (f" — {classe.filiere}" if classe.filiere else "")),
        ("Année académique", classe.annee_academique),
    ]
    for libelle, valeur in lignes:
        page.insert_text((60, y), latin1(f"{libelle} :"), fontsize=11, color=(0.35, 0.35, 0.35))
        page.insert_text((220, y), latin1(valeur), fontsize=11, color=ENCRE, fontname="hebo")
        y += 20
    return y + 10


def _attestation(db: Session, eleve: Eleve, classe: Classe, etablissement: Etablissement, demande) -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    y = _entete(page, etablissement, "Attestation de scolarité")
    page.insert_textbox(
        fitz.Rect(40, y, 555, y + 60),
        latin1(
            f"Le chef de l'établissement {etablissement.nom} atteste que l'élève désigné(e) ci-dessous est "
            f"régulièrement inscrit(e) dans l'établissement pour l'année académique {classe.annee_academique}."
        ),
        fontsize=11, color=ENCRE,
    )
    _identite(page, y + 80, eleve, classe)
    _pied(page, etablissement, demande)
    contenu = document.tobytes(garbage=3, deflate=True)
    document.close()
    return contenu


def _releve(db: Session, eleve: Eleve, classe: Classe, etablissement: Etablissement, demande) -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    y = _identite(page, _entete(page, etablissement, "Relevé de notes"), eleve, classe)
    page.insert_text((40, y), latin1("Évaluation"), fontsize=10, fontname="hebo", color=ENCRE)
    page.insert_text((330, y), latin1("Matière"), fontsize=10, fontname="hebo", color=ENCRE)
    page.insert_text((480, y), latin1("Note"), fontsize=10, fontname="hebo", color=ENCRE)
    y += 6
    page.draw_line((40, y), (555, y), color=(0.7, 0.7, 0.7), width=0.6)
    y += 16
    lignes = (
        db.query(Devoir, Soumission)
        .join(Soumission, Soumission.devoir_id == Devoir.id)
        .filter(
            Devoir.classe_id == classe.id,
            Devoir.nature == NatureEvaluation.SOMMATIVE,
            Devoir.masque_par_id.is_(None),
            Soumission.eleve_id == eleve.id,
            Soumission.statut == StatutSoumission.CORRIGEE,
        )
        .order_by(Devoir.date_limite)
        .all()
    )
    for devoir, soumission in lignes:
        if y > 690:
            break
        total = sum(q.points_max for q in devoir.questions) or 1.0
        page.insert_text((40, y), latin1(devoir.titre[:52]), fontsize=9, color=ENCRE)
        page.insert_text((330, y), latin1(devoir.matiere[:26]), fontsize=9, color=ENCRE)
        page.insert_text((480, y), latin1(f"{soumission.note:g} / {total:g}"), fontsize=9, color=ENCRE)
        y += 15
    if not lignes:
        page.insert_text((40, y), latin1("Aucune évaluation corrigée à ce jour."), fontsize=10, color=(0.4, 0.4, 0.4))
        y += 15
    bulletin = (
        db.query(Bulletin).filter(Bulletin.eleve_id == eleve.id, Bulletin.classe_id == classe.id)
        .order_by(Bulletin.updated_at.desc()).first()
    )
    if bulletin is not None:
        y += 12
        periode = periodes.trouver(etablissement.type, classe.annee_academique, bulletin.periode)
        page.insert_text((40, y), f"Moyenne générale ({periode.libelle if periode else bulletin.periode}) : {bulletin.moyenne_generale:.1f} / 100",
                         fontsize=11, fontname="hebo", color=ENCRE)
    _pied(page, etablissement, demande)
    contenu = document.tobytes(garbage=3, deflate=True)
    document.close()
    return contenu


def bulletin_favorable(db: Session, eleve: Eleve, classe: Classe) -> Bulletin | None:
    """Dernier bulletin de la classe delibere par le conseil avec une decision favorable."""
    bulletins = (
        db.query(Bulletin)
        .filter(Bulletin.eleve_id == eleve.id, Bulletin.classe_id == classe.id, Bulletin.valide_par_conseil.is_(True))
        .order_by(Bulletin.updated_at.desc())
        .all()
    )
    return next((b for b in bulletins if est_favorable(b.decision_passage)), None)


def _certificat(db: Session, eleve: Eleve, classe: Classe, etablissement: Etablissement, demande) -> bytes | None:
    bulletin = bulletin_favorable(db, eleve, classe)
    if bulletin is None:
        return None  # pas de deliberation favorable : l'A+ tranche
    periode = periodes.trouver(etablissement.type, classe.annee_academique, bulletin.periode)
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    y = _entete(page, etablissement, "Certificat de réussite")
    classe_txt = classe.niveau + (f" — {classe.filiere}" if classe.filiere else "")
    page.insert_textbox(
        fitz.Rect(40, y, 555, y + 90),
        latin1(
            f"Le chef de l'établissement {etablissement.nom} certifie que l'élève désigné(e) ci-dessous a suivi "
            f"avec succès la classe de {classe_txt} au titre de l'année académique {classe.annee_academique}. "
            f"Le conseil de classe a prononcé la décision suivante : {libelle_decision(bulletin.decision_passage)}."
        ),
        fontsize=11, color=ENCRE,
    )
    y = _identite(page, y + 100, eleve, classe)
    page.insert_text((60, y), latin1("Moyenne générale :"), fontsize=11, color=(0.35, 0.35, 0.35))
    page.insert_text((220, y), f"{bulletin.moyenne_generale:.1f} / 100" + (f" ({periode.libelle})" if periode else ""),
                     fontsize=11, color=ENCRE, fontname="hebo")
    _pied(page, etablissement, demande)
    contenu = document.tobytes(garbage=3, deflate=True)
    document.close()
    return contenu


def generer_et_livrer(db: Session, demande: DemandeActeAcademique, files_client: LuluFilesClient) -> bool:
    """Genere, televerse et livre l'acte si son type a un modele. True si livre."""
    if demande.statut != StatutDemandeActe.EN_TRAITEMENT or demande.type_acte_id is None:
        return False
    type_acte = db.get(TypeActeAcademique, demande.type_acte_id)
    if type_acte is None or type_acte.modele_document not in MODELES:
        return False
    eleve = db.get(Eleve, demande.eleve_id)
    inscription = _inscription_courante(db, eleve)
    if inscription is None:
        return False  # pas d'inscription validee : l'A+ tranche lui-meme
    classe = db.get(Classe, inscription.classe_id)
    etablissement = db.get(Etablissement, classe.etablissement_id)
    fabrique = {ATTESTATION_SCOLARITE: _attestation, RELEVE_NOTES: _releve, CERTIFICAT_REUSSITE: _certificat}[type_acte.modele_document]
    try:
        contenu = fabrique(db, eleve, classe, etablissement, demande)
        if contenu is None:
            return False
        demande.document_final_lulufiles_id = files_client.upload(contenu, f"{type_acte.modele_document}.pdf", "application/pdf")
    except FileStorageError:
        logger.warning("actes: livraison automatique impossible pour la demande %s (LuluFiles) - circuit manuel.", demande.id)
        db.rollback()
        return False
    demande.statut = StatutDemandeActe.ACCEPTEE
    db.commit()
    logger.info("actes: demande %s generee et livree automatiquement (%s).", demande.id, type_acte.modele_document)
    return True


def livrer_en_arriere_plan(session_factory: sessionmaker, demande_id: str, files_client: LuluFilesClient) -> None:
    """Pour BackgroundTasks : la session de la requete est deja fermee."""
    db = session_factory()
    try:
        demande = db.get(DemandeActeAcademique, demande_id)
        if demande is not None:
            generer_et_livrer(db, demande, files_client)
    finally:
        db.close()
