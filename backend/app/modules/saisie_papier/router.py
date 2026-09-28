"""Saisie papier (« guichet papier ») : l'administration enregistre, a partir d'une photo,
ce que les personnes sans smartphone ont produit sur papier.

Deux temps, toujours : 1) LIRE - les photos sont conservees (preuve) et l'IA propose une
lecture ; 2) ENREGISTRER - l'administrateur a relu et corrige chaque valeur, puis valide
(Art. 401 : l'IA ne decide rien). Chaque saisie est tracee dans `documents_papier`.

Couvre : feuille de notes et feuille d'appel (enseignant sans smartphone), cours ecrit,
copies d'eleves d'un devoir, fiche d'inscription au guichet et consentement signe (parent
sans smartphone), contrat signe sur papier.
"""

from __future__ import annotations

import base64
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from app.core import pdf_officiel as pdf
from app.core.database import get_db, get_session_factory
from app.core.deps import api_error, get_current_active_user, require_roles, verifier_portee_etablissement
from app.core.documents import DocumentIllisibleError, telecharger_borne
from app.core.email import BrevoEmailClient, get_email_client
from app.core.files import TYPES_DOCUMENT, FileStorageError, LuluFilesClient, get_files_client, lire_upload_borne
from app.core.llm import FreeLLMClient, LectureDocumentError, get_llm_client
from app.modules.evaluations.schemas import LienFichierOut
from app.modules.etablissements.models import AffectationEnseignant, Classe, Etablissement, annee_academique_courante
from app.modules.evaluations.models import (
    BaremeDevoir, Devoir, NatureEvaluation, QuestionDevoir, Soumission, StatutSoumission,
)
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, Nationalite, StatutInscription
from app.modules.pedagogie.models import Cours, FormatCours
from app.modules.recrutement.models import Contrat, StatutContrat
from app.modules.saisie_papier import lecture
from app.modules.saisie_papier.models import DocumentPapier, StatutDocumentPapier, TypeDocumentPapier
from app.modules.saisie_papier.schemas import (
    AppelEnregistrement, ConsentementEnAttente, ContexteClasse, CopieLue, DevoirCandidat, EnseignantCandidat, CopiesEnregistrement, CopiesLectureOut, CoursEnregistrement, DocumentPapierOut,
    EleveCandidat, InscriptionGuichet, InscriptionGuichetOut, LectureOut, LigneLue, NotesEnregistrement,
    ResultatEnregistrement,
)
from app.modules.vie_scolaire.models import EntreeVieScolaire, NatureEntreeVieScolaire

logger = logging.getLogger(__name__)
router = APIRouter(tags=["saisie-papier"])

MAX_FICHIER_OCTETS = 15 * 1024 * 1024
MAX_FICHIERS = 8
MAX_COPIES = 40
AGE_MAJORITE_NUMERIQUE = 16

_ADMINS = (RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)


# ─── Outils communs ─────────────────────────────────────────────────────────

def _eleves_de_la_classe(db: Session, classe_id: str) -> list[Eleve]:
    return (
        db.query(Eleve)
        .join(Inscription, Inscription.eleve_id == Eleve.id)
        .filter(Inscription.classe_id == classe_id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Eleve.nom, Eleve.prenom)
        .all()
    )


def _candidats(eleves: list[Eleve]) -> list[EleveCandidat]:
    return [EleveCandidat(eleve_id=e.id, nom=e.nom, prenom=e.prenom, matricule=e.matricule) for e in eleves]


def _classe_de_l_etablissement(db: Session, classe_id: str, etablissement_id: str) -> Classe:
    classe = db.get(Classe, classe_id)
    if classe is None or classe.etablissement_id != etablissement_id:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable dans cet établissement.")
    return classe


def _stocker(files_client: LuluFilesClient, contenu: bytes, nom: str, type_contenu: str) -> str:
    try:
        return files_client.upload(contenu, nom, type_contenu)
    except FileStorageError as exc:
        raise api_error(status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible d'enregistrer la photo, veuillez réessayer.") from exc


def _lire_fichiers(fichiers: list[UploadFile], maximum: int = MAX_FICHIERS) -> list[tuple[bytes, str, str]]:
    if not fichiers:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "photo_requise", "Ajoutez au moins une photo du document.")
    if len(fichiers) > maximum:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "trop_de_photos", f"{maximum} photos au maximum par envoi.")
    return [
        (lire_upload_borne(f, MAX_FICHIER_OCTETS, TYPES_DOCUMENT), f.filename or "photo", f.content_type or "image/jpeg")
        for f in fichiers
    ]


def _document(db: Session, document_id: str, utilisateur: Utilisateur, type_attendu: TypeDocumentPapier) -> DocumentPapier:
    document = db.get(DocumentPapier, document_id)
    if document is None or document.type != type_attendu:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Saisie introuvable.")
    verifier_portee_etablissement(db, utilisateur, document.etablissement_id)
    if document.statut != StatutDocumentPapier.LU:
        raise api_error(status.HTTP_409_CONFLICT, "deja_enregistre", "Ce document a déjà été enregistré.")
    return document


def _terminer(document: DocumentPapier, objet_type: str, objet_id: str | None, donnees: dict) -> None:
    document.statut = StatutDocumentPapier.ENREGISTRE
    document.objet_type, document.objet_id = objet_type, objet_id
    document.donnees_enregistrees = donnees
    document.enregistre_le = datetime.now(timezone.utc)


def _verifier_enseignant(db: Session, enseignant_id: str, classe_id: str) -> None:
    affecte = db.query(AffectationEnseignant).filter(
        AffectationEnseignant.enseignant_id == enseignant_id, AffectationEnseignant.classe_id == classe_id
    ).first()
    if affecte is None:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "enseignant_non_affecte",
                        "Cet enseignant n'est pas affecté à cette classe.")


def _eleves_autorises(db: Session, classe_id: str, eleve_ids: list[str]) -> dict[str, Eleve]:
    eleves = {e.id: e for e in _eleves_de_la_classe(db, classe_id)}
    inconnus = [i for i in eleve_ids if i not in eleves]
    if inconnus:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "eleve_hors_classe",
                        "Un des élèves choisis n'est pas inscrit dans cette classe.")
    if len(set(eleve_ids)) != len(eleve_ids):
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "eleve_en_double", "Un même élève apparaît deux fois.")
    return eleves


# ─── 1. Lire un document ────────────────────────────────────────────────────

_TYPES_LECTURE = {
    "feuille_notes": TypeDocumentPapier.FEUILLE_NOTES,
    "feuille_appel": TypeDocumentPapier.FEUILLE_APPEL,
    "cours": TypeDocumentPapier.COURS,
    "fiche_inscription": TypeDocumentPapier.FICHE_INSCRIPTION,
}


@router.post("/etablissements/{etablissement_id}/saisie-papier/lire", response_model=LectureOut)
def lire_document(
    etablissement_id: str,
    type: str = Form(...),
    classe_id: str | None = Form(None),
    fichiers: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> LectureOut:
    """Photos du document -> conservation (preuve) + lecture par l'IA + rapprochement avec
    les eleves de la classe. Si l'IA echoue, la saisie reste possible a la main."""
    verifier_portee_etablissement(db, admin, etablissement_id)
    if type not in _TYPES_LECTURE:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "type_invalide", "Type de document inconnu.")
    type_doc = _TYPES_LECTURE[type]
    eleves: list[Eleve] = []
    if type_doc in (TypeDocumentPapier.FEUILLE_NOTES, TypeDocumentPapier.FEUILLE_APPEL):
        if not classe_id:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "classe_requise", "Choisissez la classe de la feuille.")
        _classe_de_l_etablissement(db, classe_id, etablissement_id)
        eleves = _eleves_de_la_classe(db, classe_id)

    contenus = _lire_fichiers(fichiers)
    ids = [_stocker(files_client, c, nom, t) for c, nom, t in contenus]
    images = [img for c, _, t in contenus for img in lecture.images_pour_lecture(c, t)][: lecture.MAX_PAGES]

    lu, erreur = None, None
    if not images:
        erreur = "Photo illisible : reprenez-la plus nettement, ou saisissez les valeurs à la main."
    else:
        try:
            lu = llm_client.lire_document_papier(lecture.consigne(type), images)
        except LectureDocumentError:
            logger.warning("saisie papier : lecture IA impossible (%s).", type)
            erreur = "L'IA n'a pas pu lire ce document. Vous pouvez réessayer, ou saisir les valeurs à la main."

    document = DocumentPapier(etablissement_id=etablissement_id, type=type_doc, fichiers=ids, lecture_ia=lu, saisi_par_id=admin.id)
    db.add(document)
    db.commit()

    sortie = LectureOut(document_id=document.id, type=type, lecture=lu, erreur_lecture=erreur, eleves=_candidats(eleves))
    if lu and type_doc in (TypeDocumentPapier.FEUILLE_NOTES, TypeDocumentPapier.FEUILLE_APPEL):
        lignes = [l for l in (lu.get("lignes") or []) if isinstance(l, dict) and l.get("nom")]
        paires = lecture.apparier([str(l["nom"]) for l in lignes], [(e.id, e.nom, e.prenom) for e in eleves])
        for ligne, (eleve_id, score) in zip(lignes, paires):
            note = ligne.get("note")
            sortie.lignes.append(LigneLue(
                nom_lu=str(ligne["nom"]), eleve_id=eleve_id, confiance=lecture.niveau_confiance(score),
                note=float(note) if isinstance(note, (int, float)) else None,
                absent=bool(ligne.get("absent")),
                statut=ligne.get("statut") if ligne.get("statut") in ("absent", "retard") else None,
                commentaire=ligne.get("commentaire"), lisible=ligne.get("lisible", True) is not False,
            ))
    if lu and type_doc == TypeDocumentPapier.FICHE_INSCRIPTION and lu.get("classe_demandee"):
        classes = db.query(Classe).filter(
            Classe.etablissement_id == etablissement_id, Classe.annee_academique == annee_academique_courante()
        ).all()
        paires = lecture.apparier([str(lu["classe_demandee"])], [(c.id, c.niveau, c.filiere or "") for c in classes])
        sortie.classe_proposee_id = paires[0][0] if paires else None
    return sortie


# ─── 2. Enregistrer ─────────────────────────────────────────────────────────

@router.post("/saisie-papier/{document_id}/notes", response_model=ResultatEnregistrement)
def enregistrer_notes(
    document_id: str,
    payload: NotesEnregistrement,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> ResultatEnregistrement:
    """Feuille de notes -> une evaluation « sur papier » de l'enseignant (une seule question,
    notee sur le bareme de la feuille) et une copie corrigee par eleve present. Un eleve
    absent n'a pas de copie : il compte 0 dans le bulletin (regle UC-08, sans derogation)."""
    document = _document(db, document_id, admin, TypeDocumentPapier.FEUILLE_NOTES)
    classe = _classe_de_l_etablissement(db, payload.classe_id, document.etablissement_id)
    _verifier_enseignant(db, payload.enseignant_id, classe.id)
    _eleves_autorises(db, classe.id, [l.eleve_id for l in payload.lignes])
    for l in payload.lignes:
        if not l.absent and l.note is None:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "note_manquante",
                            "Chaque élève présent doit avoir une note (ou être marqué absent).")
        if l.note is not None and l.note > payload.note_sur:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "note_hors_bareme",
                            f"Une note dépasse le barème de la feuille ({payload.note_sur:g}).")

    devoir = Devoir(
        classe_id=classe.id, enseignant_id=payload.enseignant_id, titre=payload.titre.strip(), matiere=payload.matiere.strip(),
        date_limite=datetime.combine(payload.date_evaluation, time(23, 59), tzinfo=timezone.utc),
        bareme=BaremeDevoir.FLEXIBLE, nature=NatureEvaluation(payload.nature),
    )
    db.add(devoir)
    db.flush()
    db.add(QuestionDevoir(
        devoir_id=devoir.id, ordre=1, enonce="Évaluation sur papier (notes saisies par l'administration).",
        points_max=payload.note_sur, bareme_reponse="Copie corrigée sur papier par l'enseignant.",
    ))
    presents = [l for l in payload.lignes if not l.absent]
    for l in presents:
        db.add(Soumission(devoir_id=devoir.id, eleve_id=l.eleve_id, statut=StatutSoumission.CORRIGEE, note=l.note))
    _terminer(document, "devoir", devoir.id, payload.model_dump(mode="json"))
    db.commit()
    absents = len(payload.lignes) - len(presents)
    return ResultatEnregistrement(
        objet_id=devoir.id, nombre=len(presents),
        message=f"{len(presents)} note(s) enregistrée(s)" + (f", {absents} absent(s)" if absents else "") + f" pour « {devoir.titre} ».",
    )


@router.post("/saisie-papier/{document_id}/appel", response_model=ResultatEnregistrement)
def enregistrer_appel(
    document_id: str,
    payload: AppelEnregistrement,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> ResultatEnregistrement:
    """Feuille d'appel -> absences et retards dans la vie scolaire (auteur : l'administrateur,
    mention de la feuille papier). Une entree deja presente le meme jour n'est pas dupliquee."""
    document = _document(db, document_id, admin, TypeDocumentPapier.FEUILLE_APPEL)
    classe = _classe_de_l_etablissement(db, payload.classe_id, document.etablissement_id)
    if payload.date > date.today():
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "date_future", "La date de l'appel ne peut pas être dans le futur.")
    _eleves_autorises(db, classe.id, [l.eleve_id for l in payload.lignes])
    crees = 0
    for l in payload.lignes:
        nature = NatureEntreeVieScolaire.ABSENCE if l.statut == "absent" else NatureEntreeVieScolaire.RETARD
        existe = db.query(EntreeVieScolaire).filter(
            EntreeVieScolaire.eleve_id == l.eleve_id, EntreeVieScolaire.classe_id == classe.id,
            EntreeVieScolaire.nature == nature, EntreeVieScolaire.date_survenue == payload.date,
            EntreeVieScolaire.matiere == payload.matiere,
        ).first()
        if existe:
            continue
        libelle = "Absent(e)" if nature == NatureEntreeVieScolaire.ABSENCE else "En retard"
        db.add(EntreeVieScolaire(
            eleve_id=l.eleve_id, classe_id=classe.id, auteur_id=admin.id, nature=nature, matiere=payload.matiere,
            description=f"{libelle} (feuille d'appel papier)" + (f" : {l.commentaire.strip()}" if l.commentaire else ""),
            date_survenue=payload.date,
        ))
        crees += 1
    _terminer(document, "vie_scolaire", classe.id, payload.model_dump(mode="json"))
    db.commit()
    return ResultatEnregistrement(objet_id=classe.id, nombre=crees,
                                  message=f"{crees} absence(s) ou retard(s) enregistré(s) pour le {payload.date:%d/%m/%Y}.")


@router.post("/saisie-papier/{document_id}/cours", response_model=ResultatEnregistrement)
def enregistrer_cours(
    document_id: str,
    payload: CoursEnregistrement,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> ResultatEnregistrement:
    """Cours ecrit a la main -> cours texte publie au nom de l'enseignant (transcription
    relue par l'administrateur). El Professor et les quiz s'appuient ensuite dessus."""
    document = _document(db, document_id, admin, TypeDocumentPapier.COURS)
    classe = _classe_de_l_etablissement(db, payload.classe_id, document.etablissement_id)
    _verifier_enseignant(db, payload.enseignant_id, classe.id)
    cours = Cours(
        classe_id=classe.id, enseignant_id=payload.enseignant_id, titre=payload.titre.strip(),
        chapitre=payload.chapitre.strip(), format=FormatCours.TEXTE, contenu_texte=payload.contenu.strip(),
    )
    db.add(cours)
    db.flush()
    _terminer(document, "cours", cours.id, {"classe_id": classe.id, "enseignant_id": payload.enseignant_id, "titre": cours.titre})
    db.commit()
    return ResultatEnregistrement(objet_id=cours.id, nombre=1, message=f"Cours « {cours.titre} » publié pour la classe.")


def _age_a(naissance: date) -> int:
    aujourdhui = date.today()
    return aujourdhui.year - naissance.year - ((aujourdhui.month, aujourdhui.day) < (naissance.month, naissance.day))


def fiche_identifiants_pdf(etablissement: Etablissement, classe: Classe, eleve: Eleve, matricule: str, mot_de_passe: str) -> bytes:
    document = pdf.nouveau_document()
    page, y = pdf.nouvelle_page(document, etablissement, "Identifiants de connexion")
    y = pdf.champs(page, y, [
        ("Élève", f"{eleve.nom.upper()} {eleve.prenom}"),
        ("Classe", classe.niveau + (f" - {classe.filiere}" if classe.filiere else "")),
        ("Identifiant (matricule)", matricule),
        ("Mot de passe provisoire", mot_de_passe),
    ], colonne=240)
    pdf.paragraphe(page, y + 10, (
        "Pour se connecter à LuluSchools, l'élève saisit son matricule et ce mot de passe provisoire ; "
        "il devra en choisir un nouveau dès la première connexion. Conservez cette fiche en lieu sûr et ne "
        "la communiquez à personne. En cas de perte, adressez-vous à l'administration de l'établissement."
    ))
    pdf.pied(page, eleve.id, mention="Remis à la famille le {date} par l'administration de l'établissement.")
    return pdf.vers_octets(document)


@router.post("/saisie-papier/{document_id}/inscription", response_model=InscriptionGuichetOut)
def enregistrer_inscription_guichet(
    document_id: str,
    payload: InscriptionGuichet,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> InscriptionGuichetOut:
    """Inscription au guichet (famille sans smartphone ni e-mail) : la fiche papier remplie et
    signee par le parent est conservee comme preuve, l'eleve est inscrit et admis directement
    par l'administration (dans la limite des places) et ses identifiants sont imprimes."""
    from app.modules.inscriptions.router import ValidationImpossible, valider_inscription_interne

    document = _document(db, document_id, admin, TypeDocumentPapier.FICHE_INSCRIPTION)
    classe = _classe_de_l_etablissement(db, payload.classe_id, document.etablissement_id)
    mineur = _age_a(payload.date_naissance) < AGE_MAJORITE_NUMERIQUE
    if mineur and not payload.consentement_signe:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "consentement_manquant",
                        "Élève de moins de 16 ans : la fiche doit porter la signature du parent ou tuteur (consentement).")

    eleve = Eleve(nom=payload.nom.strip(), prenom=payload.prenom.strip(), date_naissance=payload.date_naissance,
                  nationalite=Nationalite(payload.nationalite), tuteur_id=None)
    db.add(eleve)
    db.flush()
    inscription = Inscription(
        eleve_id=eleve.id, classe_id=classe.id, statut=StatutInscription.SOUMISE,
        consentement_parental_horodatage=datetime.now(timezone.utc) if mineur else None,
    )
    db.add(inscription)
    db.flush()
    _terminer(document, "inscription", inscription.id, payload.model_dump(mode="json"))
    db.commit()
    try:
        mot_de_passe = valider_inscription_interne(db, inscription, email_client)
    except ValidationImpossible as exc:
        # Inscription conservee (SOUMISE) : elle apparait dans « A traiter » ; ici, on explique.
        raise api_error(status.HTTP_409_CONFLICT, exc.code, f"Inscription enregistrée mais non validée : {exc.message}") from exc
    db.refresh(eleve)
    fiche = None
    if mot_de_passe and eleve.matricule:
        etablissement = db.get(Etablissement, classe.etablissement_id)
        fiche = base64.b64encode(fiche_identifiants_pdf(etablissement, classe, eleve, eleve.matricule, mot_de_passe)).decode()
    return InscriptionGuichetOut(inscription_id=inscription.id, eleve_id=eleve.id, matricule=eleve.matricule,
                                 mot_de_passe_provisoire=mot_de_passe, fiche_identifiants_pdf=fiche)


# ─── 3. Copies d'eleves (devoir existant) ───────────────────────────────────

def _devoir_accessible(db: Session, devoir_id: str, utilisateur: Utilisateur) -> tuple[Devoir, Classe]:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    classe = db.get(Classe, devoir.classe_id)
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        if devoir.enseignant_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")
    else:
        verifier_portee_etablissement(db, utilisateur, classe.etablissement_id)
    return devoir, classe


@router.post("/devoirs/{devoir_id}/copies-papier/lire", response_model=CopiesLectureOut)
def lire_copies(
    devoir_id: str,
    fichiers: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT, *_ADMINS)),
) -> CopiesLectureOut:
    """Copies papier d'eleves sans smartphone : une photo (ou un PDF) par copie. L'IA lit le
    nom ecrit sur chaque copie et propose l'eleve ; l'utilisateur confirme ensuite."""
    devoir, classe = _devoir_accessible(db, devoir_id, utilisateur)
    deja = {s.eleve_id for s in db.query(Soumission).filter(Soumission.devoir_id == devoir.id)}
    eleves = [e for e in _eleves_de_la_classe(db, classe.id) if e.id not in deja]
    contenus = _lire_fichiers(fichiers, MAX_COPIES)
    ids = [_stocker(files_client, c, nom, t) for c, nom, t in contenus]

    def nom_ecrit(contenu: bytes, type_contenu: str) -> str | None:
        images = lecture.images_pour_lecture(contenu, type_contenu)[:1]
        if not images:
            return None
        try:
            return (llm_client.lire_document_papier(lecture.consigne("copie"), images) or {}).get("nom")
        except LectureDocumentError:
            return None

    with ThreadPoolExecutor(max_workers=6) as pool:
        noms = list(pool.map(lambda c: nom_ecrit(c[0], c[2]), contenus))
    paires = lecture.apparier([n or "" for n in noms], [(e.id, e.nom, e.prenom) for e in eleves])

    copies = []
    for (_, nom_fichier, _), file_id, nom, (eleve_id, score) in zip(contenus, ids, noms, paires):
        document = DocumentPapier(etablissement_id=classe.etablissement_id, type=TypeDocumentPapier.COPIE, fichiers=[file_id],
                                  lecture_ia={"nom": nom, "devoir_id": devoir.id}, saisi_par_id=utilisateur.id)
        db.add(document)
        db.flush()
        copies.append(CopieLue(document_id=document.id, nom_fichier=nom_fichier, nom_lu=nom, eleve_id=eleve_id,
                               confiance=lecture.niveau_confiance(score)))
    db.commit()
    return CopiesLectureOut(copies=copies, eleves=_candidats(eleves))


def telecharger_copie(files_client: LuluFilesClient, file_id: str) -> bytes:
    return telecharger_borne(files_client.get_signed_link(file_id), MAX_FICHIER_OCTETS)


def _corriger_copie(document_id: str, soumission_id: str, strict: bool, files_client: LuluFilesClient,
                    llm_client: FreeLLMClient, session_factory: sessionmaker) -> None:
    """Arriere-plan : recupere la photo de la copie et reutilise la correction holistique
    existante (evaluations). En cas d'echec : copie « a reprendre » (correction manuelle)."""
    from app.modules.evaluations.router import _corriger_copie_image_en_arriere_plan

    db = session_factory()
    try:
        document = db.get(DocumentPapier, document_id)
        type_contenu = "image/jpeg"
        try:
            contenu = telecharger_copie(files_client, document.fichiers[0])
            images = lecture.images_pour_lecture(contenu, "application/pdf" if contenu.startswith(b"%PDF") else "image/jpeg")
        except (FileStorageError, DocumentIllisibleError, httpx.HTTPError, OSError):
            images = []
        if not images:
            soumission = db.get(Soumission, soumission_id)
            soumission.statut = StatutSoumission.ECHEC_CORRECTION
            db.commit()
            return
    finally:
        db.close()
    _corriger_copie_image_en_arriere_plan(soumission_id, llm_client, strict, session_factory, images[0][0], type_contenu)


@router.post("/devoirs/{devoir_id}/copies-papier/enregistrer", response_model=ResultatEnregistrement)
def enregistrer_copies(
    devoir_id: str,
    payload: CopiesEnregistrement,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    llm_client: FreeLLMClient = Depends(get_llm_client),
    session_factory: sessionmaker = Depends(get_session_factory),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT, *_ADMINS)),
) -> ResultatEnregistrement:
    """Chaque copie confirmee devient la copie de l'eleve, corrigee par l'IA en arriere-plan
    selon le bareme du devoir. [Delegue] Autorise meme apres la date limite : la copie a ete
    rendue sur papier a temps, seule sa saisie est posterieure."""
    devoir, classe = _devoir_accessible(db, devoir_id, utilisateur)
    _eleves_autorises(db, classe.id, [a.eleve_id for a in payload.affectations])
    deja = {s.eleve_id for s in db.query(Soumission).filter(Soumission.devoir_id == devoir.id)}
    doublons = [a for a in payload.affectations if a.eleve_id in deja]
    if doublons:
        raise api_error(status.HTTP_409_CONFLICT, "deja_soumis", "Un des élèves a déjà une copie pour ce devoir.")
    creees = []
    for a in payload.affectations:
        document = db.get(DocumentPapier, a.document_id)
        if (document is None or document.type != TypeDocumentPapier.COPIE or document.statut != StatutDocumentPapier.LU
                or (document.lecture_ia or {}).get("devoir_id") != devoir.id):
            raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Copie introuvable pour ce devoir.")
        soumission = Soumission(devoir_id=devoir.id, eleve_id=a.eleve_id, statut=StatutSoumission.EN_CORRECTION,
                                copie_image_lulufiles_file_id=document.fichiers[0])
        db.add(soumission)
        db.flush()
        _terminer(document, "soumission", soumission.id, {"eleve_id": a.eleve_id, "devoir_id": devoir.id})
        creees.append((document.id, soumission.id))
    db.commit()
    for document_id, soumission_id in creees:
        background_tasks.add_task(_corriger_copie, document_id, soumission_id, devoir.bareme == BaremeDevoir.RIGIDE,
                                  files_client, llm_client, session_factory)
    return ResultatEnregistrement(objet_id=devoir.id, nombre=len(creees),
                                  message=f"{len(creees)} copie(s) enregistrée(s) : correction par l'IA en cours.")


# ─── 4. Documents signes sur papier (contrat, consentement) ─────────────────

@router.post("/contrats/{contrat_id}/signature-papier", response_model=ResultatEnregistrement)
def signer_contrat_sur_papier(
    contrat_id: str,
    fichiers: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> ResultatEnregistrement:
    """Enseignant sans smartphone : il signe le contrat imprime (PDF du contrat), l'A+ en
    enregistre la photo. Le scan est conserve comme preuve de la signature manuscrite."""
    import hashlib

    contrat = db.get(Contrat, contrat_id)
    if contrat is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Contrat introuvable.")
    verifier_portee_etablissement(db, admin, contrat.etablissement_id)
    if contrat.statut != StatutContrat.EN_ATTENTE_SIGNATURE:
        raise api_error(status.HTTP_409_CONFLICT, "deja_signe", "Ce contrat est déjà signé.")
    ids = [_stocker(files_client, c, nom, t) for c, nom, t in _lire_fichiers(fichiers)]  # une photo par page
    contrat.statut = StatutContrat.SIGNE
    contrat.signature_horodatage = datetime.now(timezone.utc)
    contrat.signature_hash_document = hashlib.sha256(contrat.syllabus.encode("utf-8")).hexdigest()
    contrat.signature_image_lulufiles_id = ids[-1]  # « Voir la signature » : derniere page (celle qui porte la signature)
    document = DocumentPapier(etablissement_id=contrat.etablissement_id, type=TypeDocumentPapier.CONTRAT_SIGNE,
                              fichiers=ids, saisi_par_id=admin.id)
    db.add(document)
    _terminer(document, "contrat", contrat.id, {"contrat_id": contrat.id})
    db.commit()
    return ResultatEnregistrement(objet_id=contrat.id, nombre=1, message="Contrat enregistré comme signé sur papier.")


@router.post("/inscriptions/{inscription_id}/consentement-papier", response_model=ResultatEnregistrement)
def consentement_sur_papier(
    inscription_id: str,
    fichiers: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    email_client: BrevoEmailClient = Depends(get_email_client),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> ResultatEnregistrement:
    """Parent sans smartphone : il signe le formulaire de consentement au guichet (Art. 389-390,
    446 : consentement du parent, demontrable) ; l'A+ en enregistre la photo."""
    from app.modules.inscriptions.router import admettre_automatiquement

    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")
    classe = db.get(Classe, inscription.classe_id)
    verifier_portee_etablissement(db, admin, classe.etablissement_id)
    if inscription.statut != StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL:
        raise api_error(status.HTTP_409_CONFLICT, "consentement_non_attendu", "Cette inscription n'attend pas de consentement parental.")
    ids = [_stocker(files_client, c, nom, t) for c, nom, t in _lire_fichiers(fichiers)]
    inscription.statut = StatutInscription.SOUMISE
    inscription.consentement_parental_horodatage = datetime.now(timezone.utc)
    document = DocumentPapier(etablissement_id=classe.etablissement_id, type=TypeDocumentPapier.CONSENTEMENT,
                              fichiers=ids, saisi_par_id=admin.id)
    db.add(document)
    _terminer(document, "inscription", inscription.id, {"inscription_id": inscription.id})
    db.commit()
    admettre_automatiquement(db, inscription, email_client)
    return ResultatEnregistrement(objet_id=inscription.id, nombre=1, message="Consentement parental enregistré (formulaire papier).")


# ─── 5. Historique et preuves ───────────────────────────────────────────────

_RESUMES = {
    TypeDocumentPapier.FEUILLE_NOTES: lambda d: f"{d.get('titre', '')} - {d.get('matiere', '')} ({len(d.get('lignes', []))} élèves)",
    TypeDocumentPapier.FEUILLE_APPEL: lambda d: f"Appel du {d.get('date', '')} ({len(d.get('lignes', []))} absence(s)/retard(s))",
    TypeDocumentPapier.COURS: lambda d: d.get("titre"),
    TypeDocumentPapier.FICHE_INSCRIPTION: lambda d: f"{d.get('prenom', '')} {d.get('nom', '')}",
}


@router.get("/etablissements/{etablissement_id}/saisie-papier/historique", response_model=list[DocumentPapierOut])
def historique(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> list[DocumentPapierOut]:
    verifier_portee_etablissement(db, admin, etablissement_id)
    documents = (
        db.query(DocumentPapier).filter(DocumentPapier.etablissement_id == etablissement_id)
        .order_by(DocumentPapier.created_at.desc()).limit(200).all()
    )
    auteurs = {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_({d.saisi_par_id for d in documents}))} if documents else {}
    sortie = []
    for d in documents:
        resume = _RESUMES.get(d.type)
        sortie.append(DocumentPapierOut(
            id=d.id, type=d.type.value, statut=d.statut.value, nombre_fichiers=len(d.fichiers or []), objet_type=d.objet_type,
            objet_id=d.objet_id, saisi_par=f"{auteurs[d.saisi_par_id].prenom} {auteurs[d.saisi_par_id].nom}",
            created_at=d.created_at, enregistre_le=d.enregistre_le,
            resume=resume(d.donnees_enregistrees) if resume and d.donnees_enregistrees else None,
        ))
    return sortie


@router.get("/saisie-papier/{document_id}/fichiers/{index}/lien", response_model=LienFichierOut)
def lien_photo(
    document_id: str,
    index: int,
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    utilisateur: Utilisateur = Depends(get_current_active_user),
) -> LienFichierOut:
    """Photo originale (preuve) : administration de l'etablissement, ou l'enseignant qui a
    saisi des copies."""
    document = db.get(DocumentPapier, document_id)
    if document is None or not (0 <= index < len(document.fichiers or [])):
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Photo introuvable.")
    if not (utilisateur.role == RoleUtilisateur.ENSEIGNANT and document.saisi_par_id == utilisateur.id):
        verifier_portee_etablissement(db, utilisateur, document.etablissement_id)
    try:
        url = files_client.get_signed_link(document.fichiers[index], disposition="inline")
    except FileStorageError as exc:
        raise api_error(status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible d'obtenir la photo, veuillez réessayer.") from exc
    return LienFichierOut(url=url)


# ─── 6. Contexte pour l'ecran de saisie ─────────────────────────────────────

@router.get("/classes/{classe_id}/saisie-papier/contexte", response_model=ContexteClasse)
def contexte_classe(
    classe_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> ContexteClasse:
    """Eleves, enseignants affectes (avec leur matiere) et devoirs de la classe : de quoi
    remplir les listes de l'ecran de saisie papier."""
    from app.modules.etablissements.affectations_auto import enseignants_sous_contrat

    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    verifier_portee_etablissement(db, admin, classe.etablissement_id)
    matieres = enseignants_sous_contrat(db, classe.etablissement_id)
    ids = [a.enseignant_id for a in db.query(AffectationEnseignant).filter(AffectationEnseignant.classe_id == classe_id)]
    enseignants = db.query(Utilisateur).filter(Utilisateur.id.in_(ids)).order_by(Utilisateur.nom).all() if ids else []
    devoirs = db.query(Devoir).filter(Devoir.classe_id == classe_id, Devoir.masque_par_id.is_(None)).order_by(Devoir.date_limite.desc()).all()
    copies = {d: n for d, n in db.query(Soumission.devoir_id, func.count(Soumission.id)).filter(
        Soumission.devoir_id.in_([d.id for d in devoirs])).group_by(Soumission.devoir_id)} if devoirs else {}
    return ContexteClasse(
        eleves=_candidats(_eleves_de_la_classe(db, classe_id)),
        enseignants=[EnseignantCandidat(id=u.id, nom=u.nom, prenom=u.prenom, matiere=matieres.get(u.id)) for u in enseignants],
        devoirs=[DevoirCandidat(id=d.id, titre=d.titre, matiere=d.matiere, date_limite=d.date_limite, copies=copies.get(d.id, 0)) for d in devoirs],
    )


@router.get("/etablissements/{etablissement_id}/saisie-papier/consentements-en-attente", response_model=list[ConsentementEnAttente])
def consentements_en_attente(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(*_ADMINS)),
) -> list[ConsentementEnAttente]:
    verifier_portee_etablissement(db, admin, etablissement_id)
    lignes = (
        db.query(Inscription, Eleve, Classe)
        .join(Eleve, Eleve.id == Inscription.eleve_id)
        .join(Classe, Classe.id == Inscription.classe_id)
        .filter(Classe.etablissement_id == etablissement_id,
                Inscription.statut == StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL)
        .order_by(Inscription.created_at)
        .all()
    )
    return [ConsentementEnAttente(inscription_id=i.id, eleve=f"{e.prenom} {e.nom}", classe=c.niveau + (f" — {c.filiere}" if c.filiere else ""),
                                  depose_le=i.created_at) for i, e, c in lignes]
