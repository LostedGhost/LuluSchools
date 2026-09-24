from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.core.files import FileStorageError, LuluFilesClient, get_files_client
from app.modules.etablissements.models import AdminEtablissement, Classe
from app.modules.evaluations.models import (
    Bulletin,
    Devoir,
    ReferentielCoefficient,
    Soumission,
    StatutReferentiel,
    StatutSoumission,
)
from app.modules.evaluations.schemas import (
    BulletinOut,
    CorrectionRequest,
    DevoirCreate,
    DevoirOut,
    ReferentielCreate,
    ReferentielOut,
    ReferentielPropositionCreate,
    SoumissionOut,
    ValiderPassageRequest,
)
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve
from app.modules.pedagogie.router import _verifier_eleve_inscrit, _verifier_enseignant_rattache

router = APIRouter(tags=["evaluations"])


@router.post("/classes/{classe_id}/devoirs", response_model=DevoirOut, status_code=status.HTTP_201_CREATED)
def creer_devoir(
    classe_id: str,
    payload: DevoirCreate,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Devoir:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    _verifier_enseignant_rattache(db, enseignant, classe.etablissement_id)

    devoir = Devoir(
        classe_id=classe_id,
        enseignant_id=enseignant.id,
        titre=payload.titre,
        date_limite=payload.date_limite,
        bareme=payload.bareme,
    )
    db.add(devoir)
    db.commit()
    db.refresh(devoir)
    return devoir


@router.get("/devoirs/{devoir_id}", response_model=DevoirOut)
def obtenir_devoir(
    devoir_id: str, db: Session = Depends(get_db), _utilisateur: Utilisateur = Depends(require_roles(
        RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ELEVE, RoleUtilisateur.ADMIN_ETABLISSEMENT
    ))
) -> Devoir:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    return devoir


@router.post(
    "/devoirs/{devoir_id}/soumissions", response_model=SoumissionOut, status_code=status.HTTP_201_CREATED
)
def soumettre_devoir(
    devoir_id: str,
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    files_client: LuluFilesClient = Depends(get_files_client),
    eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE)),
) -> Soumission:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    eleve = _verifier_eleve_inscrit(db, eleve_utilisateur.id, devoir.classe_id)

    date_limite = devoir.date_limite if devoir.date_limite.tzinfo else devoir.date_limite.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > date_limite:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "delai_depasse",
            "La date limite est depassee : la note zero s'applique automatiquement, sans derogation.",
        )

    if db.query(Soumission).filter(Soumission.devoir_id == devoir_id, Soumission.eleve_id == eleve.id).first():
        raise api_error(status.HTTP_409_CONFLICT, "deja_soumis", "Vous avez deja soumis ce devoir.")

    contenu = fichier.file.read()
    try:
        lulufiles_file_id = files_client.upload(
            contenu, fichier.filename or "soumission", fichier.content_type or "application/octet-stream"
        )
    except FileStorageError as exc:
        raise api_error(
            status.HTTP_502_BAD_GATEWAY, "stockage_echoue", "Impossible de stocker le fichier, veuillez reessayer."
        ) from exc

    soumission = Soumission(
        devoir_id=devoir_id, eleve_id=eleve.id, lulufiles_file_id=lulufiles_file_id, statut=StatutSoumission.A_TEMPS
    )
    db.add(soumission)
    db.commit()
    db.refresh(soumission)
    return soumission


@router.post("/soumissions/{soumission_id}/corriger", response_model=SoumissionOut)
def corriger_soumission(
    soumission_id: str,
    payload: CorrectionRequest,
    db: Session = Depends(get_db),
    enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Soumission:
    soumission = db.get(Soumission, soumission_id)
    if soumission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Soumission introuvable.")
    devoir = db.get(Devoir, soumission.devoir_id)
    if devoir.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")

    soumission.note = payload.note
    soumission.statut = StatutSoumission.CORRIGEE
    db.commit()
    db.refresh(soumission)
    return soumission


@router.post(
    "/referentiels-coefficients", response_model=ReferentielOut, status_code=status.HTTP_201_CREATED
)
def creer_referentiel(
    payload: ReferentielCreate,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ReferentielCoefficient:
    referentiel = ReferentielCoefficient(
        niveau=payload.niveau,
        matiere=payload.matiere,
        coefficient=payload.coefficient,
        statut=StatutReferentiel.VALIDE,
    )
    db.add(referentiel)
    db.commit()
    db.refresh(referentiel)
    return referentiel


@router.post(
    "/referentiels-coefficients/{referentiel_id}/proposition",
    response_model=ReferentielOut,
    status_code=status.HTTP_201_CREATED,
)
def proposer_mise_a_jour_referentiel(
    referentiel_id: str,
    payload: ReferentielPropositionCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> ReferentielCoefficient:
    existant = db.get(ReferentielCoefficient, referentiel_id)
    if existant is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Referentiel introuvable.")
    lien = db.get(AdminEtablissement, admin.id)

    proposition = ReferentielCoefficient(
        niveau=existant.niveau,
        matiere=existant.matiere,
        coefficient=payload.coefficient,
        statut=StatutReferentiel.PROPOSITION_EN_ATTENTE,
        etablissement_proposant_id=lien.etablissement_id if lien else None,
        propose_pour_id=existant.id,
    )
    db.add(proposition)
    db.commit()
    db.refresh(proposition)
    return proposition


@router.post("/referentiels-coefficients/{referentiel_id}/valider", response_model=ReferentielOut)
def valider_referentiel(
    referentiel_id: str,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ReferentielCoefficient:
    proposition = db.get(ReferentielCoefficient, referentiel_id)
    if proposition is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Referentiel introuvable.")
    if proposition.statut != StatutReferentiel.PROPOSITION_EN_ATTENTE:
        raise api_error(status.HTTP_409_CONFLICT, "statut_invalide", "Ce referentiel n'est pas une proposition en attente.")

    proposition.statut = StatutReferentiel.VALIDE
    if proposition.propose_pour_id:
        ancien = db.get(ReferentielCoefficient, proposition.propose_pour_id)
        if ancien is not None:
            ancien.statut = StatutReferentiel.REMPLACE

    db.commit()
    db.refresh(proposition)
    return proposition


def _calculer_et_enregistrer_bulletin(db: Session, eleve: Eleve, classe_id: str, periode: str) -> Bulletin:
    devoirs = (
        db.query(Devoir)
        .filter(Devoir.classe_id == classe_id, Devoir.date_limite < datetime.now(timezone.utc))
        .all()
    )
    notes = []
    for devoir in devoirs:
        soumission = (
            db.query(Soumission)
            .filter(Soumission.devoir_id == devoir.id, Soumission.eleve_id == eleve.id)
            .first()
        )
        if soumission is None:
            notes.append(0.0)
        elif soumission.note is not None:
            notes.append(soumission.note)
        # soumission existante mais pas encore corrigee : exclue du calcul pour l'instant

    if not notes:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "aucun_devoir_evalue", "Aucun devoir clos et evalue pour cette periode."
        )

    moyenne = sum(notes) / len(notes)

    bulletin = (
        db.query(Bulletin)
        .filter(Bulletin.eleve_id == eleve.id, Bulletin.classe_id == classe_id, Bulletin.periode == periode)
        .first()
    )
    if bulletin is None:
        bulletin = Bulletin(eleve_id=eleve.id, classe_id=classe_id, periode=periode, moyenne_generale=moyenne)
        db.add(bulletin)
    else:
        bulletin.moyenne_generale = moyenne
    db.commit()
    db.refresh(bulletin)
    return bulletin


@router.get("/eleves/{eleve_utilisateur_id}/bulletins", response_model=BulletinOut)
def obtenir_bulletin(
    eleve_utilisateur_id: str,
    classe_id: str,
    periode: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(
        RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR, RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ADMIN_ETABLISSEMENT
    )),
) -> Bulletin:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Eleve introuvable.")

    if utilisateur.role == RoleUtilisateur.ELEVE and utilisateur.id != eleve_utilisateur_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce bulletin ne vous appartient pas.")
    if utilisateur.role == RoleUtilisateur.TUTEUR and eleve.tuteur_id != utilisateur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte.")
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        classe = db.get(Classe, classe_id)
        _verifier_enseignant_rattache(db, utilisateur, classe.etablissement_id)
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        classe = db.get(Classe, classe_id)
        lien = db.get(AdminEtablissement, utilisateur.id)
        if lien is None or lien.etablissement_id != classe.etablissement_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")

    return _calculer_et_enregistrer_bulletin(db, eleve, classe_id, periode)


@router.post("/bulletins/{bulletin_id}/valider-passage", response_model=BulletinOut)
def valider_passage(
    bulletin_id: str,
    payload: ValiderPassageRequest,
    db: Session = Depends(get_db),
    _enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT)),
) -> Bulletin:
    """UC-09 : le calcul automatique ne decide jamais seul d'une decision lourde
    (passage/redoublement/diplome) - toujours une action humaine explicite."""
    bulletin = db.get(Bulletin, bulletin_id)
    if bulletin is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Bulletin introuvable.")

    bulletin.decision_passage = payload.decision
    bulletin.valide_par_conseil = True
    db.commit()
    db.refresh(bulletin)
    return bulletin
