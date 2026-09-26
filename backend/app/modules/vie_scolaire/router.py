from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles, verifier_portee_etablissement
from app.modules.etablissements.models import AffectationEnseignant, Classe
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.vie_scolaire.models import EntreeVieScolaire, _aujourdhui
from app.modules.vie_scolaire.schemas import EntreeVieScolaireCreate, EntreeVieScolaireOut

router = APIRouter(tags=["vie-scolaire"])


def _affectation_de(db: Session, enseignant_id: str, classe_id: str) -> AffectationEnseignant | None:
    return (
        db.query(AffectationEnseignant)
        .filter(AffectationEnseignant.enseignant_id == enseignant_id, AffectationEnseignant.classe_id == classe_id)
        .first()
    )


def _verifier_eleve_de_la_classe(db: Session, eleve_id: str, classe_id: str) -> Eleve:
    eleve = db.get(Eleve, eleve_id)
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Eleve introuvable.")
    inscrit = (
        db.query(Inscription)
        .filter(
            Inscription.eleve_id == eleve_id,
            Inscription.classe_id == classe_id,
            Inscription.statut == StatutInscription.VALIDEE,
        )
        .first()
    )
    if inscrit is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Cet eleve n'est pas inscrit dans cette classe.")
    return eleve


@router.post(
    "/classes/{classe_id}/eleves/{eleve_id}/vie-scolaire",
    response_model=EntreeVieScolaireOut,
    status_code=status.HTTP_201_CREATED,
)
def creer_entree_vie_scolaire(
    classe_id: str,
    eleve_id: str,
    payload: EntreeVieScolaireCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    ),
) -> EntreeVieScolaire:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    _verifier_eleve_de_la_classe(db, eleve_id, classe_id)

    est_professeur_principal = False
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        affectation = _affectation_de(db, utilisateur.id, classe_id)
        if affectation is None:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette classe ne vous est pas affectee.")
        est_professeur_principal = affectation.est_professeur_principal
    else:
        verifier_portee_etablissement(db, utilisateur, classe.etablissement_id)

    if payload.matiere is None and not est_professeur_principal and utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "matiere_requise",
            "Un enseignant de matiere doit preciser la matiere - seul le professeur principal ou "
            "l'administration peut consigner une entree globale.",
        )

    entree = EntreeVieScolaire(
        eleve_id=eleve_id,
        classe_id=classe_id,
        auteur_id=utilisateur.id,
        nature=payload.nature,
        matiere=payload.matiere,
        description=payload.description.strip(),
        date_survenue=payload.date_survenue or _aujourdhui(),
    )
    db.add(entree)
    db.commit()
    db.refresh(entree)
    return entree


def _verifier_lecture_vie_scolaire(
    db: Session, utilisateur: Utilisateur, classe: Classe, eleve: Eleve
) -> bool:
    """Renvoie True si l'appelant voit TOUT (admin/PP/tuteur/eleve lui-meme), False s'il
    ne doit voir QUE ses propres entrees (enseignant de matiere ordinaire) - voir
    EntreeVieScolaire pour la justification de cette regle de portee."""
    if utilisateur.role == RoleUtilisateur.ADMIN_MINISTERIEL:
        return True
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        verifier_portee_etablissement(db, utilisateur, classe.etablissement_id)
        return True
    if utilisateur.role == RoleUtilisateur.TUTEUR:
        if eleve.tuteur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte.")
        return True
    if utilisateur.role == RoleUtilisateur.ELEVE:
        if eleve.utilisateur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Ce dossier ne vous appartient pas.")
        return True
    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        affectation = _affectation_de(db, utilisateur.id, classe.id)
        if affectation is None:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette classe ne vous est pas affectee.")
        return affectation.est_professeur_principal
    raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Role insuffisant pour cette action.")


@router.get(
    "/classes/{classe_id}/eleves/{eleve_id}/vie-scolaire", response_model=list[EntreeVieScolaireOut]
)
def lister_vie_scolaire_eleve(
    classe_id: str,
    eleve_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(
            RoleUtilisateur.ENSEIGNANT,
            RoleUtilisateur.ADMIN_ETABLISSEMENT,
            RoleUtilisateur.ADMIN_MINISTERIEL,
            RoleUtilisateur.TUTEUR,
            RoleUtilisateur.ELEVE,
        )
    ),
) -> list[EntreeVieScolaire]:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")
    eleve = _verifier_eleve_de_la_classe(db, eleve_id, classe_id)

    voit_tout = _verifier_lecture_vie_scolaire(db, utilisateur, classe, eleve)

    requete = db.query(EntreeVieScolaire).filter(
        EntreeVieScolaire.classe_id == classe_id, EntreeVieScolaire.eleve_id == eleve_id
    )
    if not voit_tout:
        requete = requete.filter(EntreeVieScolaire.auteur_id == utilisateur.id)
    return requete.order_by(EntreeVieScolaire.date_survenue.desc(), EntreeVieScolaire.created_at.desc()).all()


@router.get("/classes/{classe_id}/vie-scolaire", response_model=list[EntreeVieScolaireOut])
def lister_vie_scolaire_de_la_classe(
    classe_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)
    ),
) -> list[EntreeVieScolaire]:
    """Vue d'ensemble (conseil de classe) - reservee a l'administration et au professeur
    principal, jamais a un enseignant de matiere ordinaire (qui n'a de toute facon acces
    qu'a ses propres entrees, classe par classe, eleve par eleve)."""
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Classe introuvable.")

    if utilisateur.role == RoleUtilisateur.ENSEIGNANT:
        affectation = _affectation_de(db, utilisateur.id, classe_id)
        if affectation is None or not affectation.est_professeur_principal:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "acces_refuse",
                "Seul le professeur principal de cette classe a une vue d'ensemble.",
            )
    else:
        verifier_portee_etablissement(db, utilisateur, classe.etablissement_id)

    return (
        db.query(EntreeVieScolaire)
        .filter(EntreeVieScolaire.classe_id == classe_id)
        .order_by(EntreeVieScolaire.date_survenue.desc(), EntreeVieScolaire.created_at.desc())
        .all()
    )
