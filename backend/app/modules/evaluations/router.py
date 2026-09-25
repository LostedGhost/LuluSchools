from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.core.llm import CorrectionError, FreeLLMClient, get_llm_client
from app.modules.etablissements.models import AdminEtablissement, Classe
from app.modules.evaluations.models import (
    Bulletin,
    Devoir,
    QuestionDevoir,
    ReferentielCoefficient,
    ReponseSoumission,
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
    SoumissionCreate,
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
        matiere=payload.matiere,
        date_limite=payload.date_limite,
        bareme=payload.bareme,
    )
    db.add(devoir)
    db.flush()
    for ordre, question in enumerate(payload.questions):
        db.add(
            QuestionDevoir(
                devoir_id=devoir.id,
                ordre=ordre,
                enonce=question.enonce,
                bareme_reponse=question.bareme_reponse,
                points_max=question.points_max,
            )
        )
    db.commit()
    db.refresh(devoir)
    return devoir


@router.get("/devoirs/{devoir_id}", response_model=DevoirOut)
def obtenir_devoir(
    devoir_id: str,
    db: Session = Depends(get_db),
    _utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ELEVE, RoleUtilisateur.ADMIN_ETABLISSEMENT)
    ),
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
    payload: SoumissionCreate,
    db: Session = Depends(get_db),
    llm_client: FreeLLMClient = Depends(get_llm_client),
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

    questions_par_id = {q.id: q for q in devoir.questions}
    if {r.question_id for r in payload.reponses} != set(questions_par_id.keys()):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "reponses_incompletes",
            "Une reponse est attendue pour chaque question du devoir, exactement.",
        )

    soumission = Soumission(devoir_id=devoir_id, eleve_id=eleve.id, statut=StatutSoumission.CORRIGEE)
    db.add(soumission)
    db.flush()

    echec = False
    reponses_orm = []
    for reponse in payload.reponses:
        question = questions_par_id[reponse.question_id]
        reponse_orm = ReponseSoumission(
            soumission_id=soumission.id, question_id=question.id, texte_reponse=reponse.texte_reponse
        )
        try:
            reponse_orm.points_obtenus = llm_client.corriger_reponse(
                question.enonce,
                question.bareme_reponse,
                question.points_max,
                reponse.texte_reponse,
                strict=(devoir.bareme.value == "rigide"),
            )
        except CorrectionError:
            echec = True
        db.add(reponse_orm)
        reponses_orm.append(reponse_orm)

    if echec:
        soumission.statut = StatutSoumission.ECHEC_CORRECTION
        soumission.note = None
    else:
        soumission.note = sum(r.points_obtenus for r in reponses_orm)

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
    """Ecran de revision manuelle : sert a la fois de filet de secours quand la
    correction automatique a echoue (statut=echec_correction) et de possibilite de
    surcharger une correction LLM deja faite."""
    soumission = db.get(Soumission, soumission_id)
    if soumission is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Soumission introuvable.")
    devoir = db.get(Devoir, soumission.devoir_id)
    if devoir.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")

    points_max_par_question = {q.id: q.points_max for q in devoir.questions}
    reponses_par_id = {r.question_id: r for r in soumission.reponses}
    for correction in payload.reponses:
        if correction.question_id not in reponses_par_id:
            raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "question_inconnue", "Question hors de ce devoir.")
        if correction.points_obtenus > points_max_par_question[correction.question_id]:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "points_hors_bareme", "points_obtenus depasse points_max."
            )
        reponses_par_id[correction.question_id].points_obtenus = correction.points_obtenus

    soumission.note = sum(r.points_obtenus or 0 for r in soumission.reponses)
    soumission.statut = StatutSoumission.CORRIGEE
    db.commit()
    db.refresh(soumission)
    return soumission


@router.get("/devoirs/{devoir_id}/soumissions-a-revoir", response_model=list[SoumissionOut])
def lister_soumissions_a_revoir(
    devoir_id: str, db: Session = Depends(get_db), enseignant: Utilisateur = Depends(require_roles(RoleUtilisateur.ENSEIGNANT))
) -> list[Soumission]:
    devoir = db.get(Devoir, devoir_id)
    if devoir is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Devoir introuvable.")
    if devoir.enseignant_id != enseignant.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce devoir ne vous appartient pas.")
    return (
        db.query(Soumission)
        .filter(Soumission.devoir_id == devoir_id, Soumission.statut == StatutSoumission.ECHEC_CORRECTION)
        .all()
    )


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


def _coefficient_pour(db: Session, niveau: str, matiere: str) -> float:
    referentiel = (
        db.query(ReferentielCoefficient)
        .filter(
            ReferentielCoefficient.niveau == niveau,
            ReferentielCoefficient.matiere == matiere,
            ReferentielCoefficient.statut == StatutReferentiel.VALIDE,
        )
        .first()
    )
    return referentiel.coefficient if referentiel is not None else 1.0


def _calculer_et_enregistrer_bulletin(db: Session, eleve: Eleve, classe_id: str, periode: str) -> Bulletin:
    """Moyenne PONDEREE : chaque devoir est normalise sur 100 (note / somme des
    points_max de ses questions), puis pondere par le coefficient (niveau, matiere) du
    referentiel valide en vigueur - defaut 1.0 si aucun referentiel ne couvre la
    matiere (UC-09). Un devoir compte des qu'il est corrige (meme avant son echeance
    formelle) ; sans soumission, il ne compte comme 0 qu'une fois l'echeance passee -
    avant, on n'a simplement pas encore de resultat a inclure."""
    classe = db.get(Classe, classe_id)
    devoirs = db.query(Devoir).filter(Devoir.classe_id == classe_id).all()

    notes_ponderees = []
    poids_total = 0.0
    for devoir in devoirs:
        points_max_devoir = sum(q.points_max for q in devoir.questions) or 1.0
        soumission = (
            db.query(Soumission)
            .filter(Soumission.devoir_id == devoir.id, Soumission.eleve_id == eleve.id)
            .first()
        )
        date_limite = devoir.date_limite if devoir.date_limite.tzinfo else devoir.date_limite.replace(tzinfo=timezone.utc)
        devoir_clos = datetime.now(timezone.utc) > date_limite

        if soumission is None:
            if not devoir_clos:
                continue  # pas encore d'echeance passee : rien a compter pour l'instant
            note_normalisee = 0.0
        elif soumission.statut == StatutSoumission.CORRIGEE and soumission.note is not None:
            note_normalisee = (soumission.note / points_max_devoir) * 100
        else:
            continue  # echec_correction en attente de revision manuelle : exclu pour l'instant

        coefficient = _coefficient_pour(db, classe.niveau, devoir.matiere)
        notes_ponderees.append(note_normalisee * coefficient)
        poids_total += coefficient

    if poids_total == 0:
        raise api_error(
            status.HTTP_404_NOT_FOUND, "aucun_devoir_evalue", "Aucun devoir clos et evalue pour cette periode."
        )

    moyenne = sum(notes_ponderees) / poids_total

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
    utilisateur: Utilisateur = Depends(
        require_roles(
            RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR, RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ADMIN_ETABLISSEMENT
        )
    ),
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
