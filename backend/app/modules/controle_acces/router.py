from fastapi import APIRouter, Depends, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles, verifier_portee_etablissement
from app.modules.controle_acces.models import DesignationControleur, ServiceControle
from app.modules.controle_acces.schemas import (
    DesignationControleurCreate,
    DesignationControleurOut,
    UtilisateurDesignableOut,
)
from app.modules.etablissements.models import AdminEtablissement, Etablissement
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.recrutement.models import Contrat, StatutContrat

router = APIRouter(tags=["controle-acces"])


def verifier_admin_de_l_etablissement(db: Session, utilisateur: Utilisateur, etablissement_id: str) -> None:
    verifier_portee_etablissement(db, utilisateur, etablissement_id)


def est_controleur_designe(
    db: Session, utilisateur_id: str, etablissement_id: str, service: ServiceControle, evenement_id: str | None = None
) -> bool:
    """Reutilise par services_scolaires et billetterie pour verifier qu'un utilisateur
    est bien le Controleur/Ticketeur designe avant de le laisser valider un ticket/billet."""
    query = db.query(DesignationControleur).filter(
        DesignationControleur.utilisateur_id == utilisateur_id,
        DesignationControleur.etablissement_id == etablissement_id,
        DesignationControleur.service == service,
    )
    if service == ServiceControle.EVENEMENT:
        query = query.filter(DesignationControleur.evenement_id == evenement_id)
    return query.first() is not None


def _est_designable(db: Session, etablissement_id: str, utilisateur_id: str) -> bool:
    sous_contrat = (
        db.query(Contrat)
        .filter(
            Contrat.enseignant_id == utilisateur_id,
            Contrat.etablissement_id == etablissement_id,
            Contrat.statut == StatutContrat.SIGNE,
        )
        .first()
        is not None
    )
    lien_admin = db.get(AdminEtablissement, utilisateur_id)
    return sous_contrat or (lien_admin is not None and lien_admin.etablissement_id == etablissement_id)


@router.get(
    "/etablissements/{etablissement_id}/utilisateurs-designables", response_model=list[UtilisateurDesignableOut]
)
def rechercher_utilisateurs_designables(
    etablissement_id: str,
    q: str | None = None,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[Utilisateur]:
    """UC-28 : recherche par nom pour la designation de controleur, meme pattern que la
    recherche d'enseignant pour l'affectation enseignant<->classe (voir
    recrutement/router.py::rechercher_enseignants_signes) - remplace la saisie d'un id
    utilisateur brut. Un controleur n'est pas necessairement un enseignant : on propose
    ici les enseignants sous contrat SIGNE avec cet etablissement et les admins de cet
    etablissement (les profils plausibles pour ce role de confiance)."""
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Établissement introuvable.")
    verifier_portee_etablissement(db, admin, etablissement_id)

    filtre_nom = (
        or_(Utilisateur.nom.ilike(f"%{q.strip()}%"), Utilisateur.prenom.ilike(f"%{q.strip()}%"))
        if q and q.strip()
        else None
    )

    enseignants = (
        db.query(Utilisateur)
        .join(Contrat, Contrat.enseignant_id == Utilisateur.id)
        .filter(Contrat.etablissement_id == etablissement_id, Contrat.statut == StatutContrat.SIGNE)
    )
    admins = (
        db.query(Utilisateur)
        .join(AdminEtablissement, AdminEtablissement.utilisateur_id == Utilisateur.id)
        .filter(AdminEtablissement.etablissement_id == etablissement_id)
    )
    if filtre_nom is not None:
        enseignants = enseignants.filter(filtre_nom)
        admins = admins.filter(filtre_nom)

    resultat = list({u.id: u for u in [*enseignants.all(), *admins.all()]}.values())
    resultat.sort(key=lambda u: u.nom)
    return resultat[:20]


@router.post(
    "/etablissements/{etablissement_id}/controleurs",
    response_model=DesignationControleurOut,
    status_code=status.HTTP_201_CREATED,
)
def designer_controleur(
    etablissement_id: str,
    payload: DesignationControleurCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> DesignationControleur:
    if db.get(Etablissement, etablissement_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Établissement introuvable.")
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)

    if db.get(Utilisateur, payload.utilisateur_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Utilisateur à désigner introuvable.")
    # Arbitrage du 2026-09-27 : meme perimetre que la recherche ci-dessus (enseignant sous
    # contrat signe ou admin de CET etablissement) - un controleur valide des titres payes,
    # role de confiance qui ne se confie pas a n'importe quel compte de la plateforme.
    if not _est_designable(db, etablissement_id, payload.utilisateur_id):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "non_designable",
            "Seuls un enseignant sous contrat ou un administrateur de l'établissement peuvent être désignés.",
        )

    designation = DesignationControleur(
        etablissement_id=etablissement_id,
        utilisateur_id=payload.utilisateur_id,
        service=payload.service,
        evenement_id=payload.evenement_id,
    )
    db.add(designation)
    db.commit()
    db.refresh(designation)
    return designation


@router.get(
    "/etablissements/{etablissement_id}/controleurs", response_model=list[DesignationControleurOut]
)
def lister_controleurs(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[DesignationControleur]:
    verifier_admin_de_l_etablissement(db, admin, etablissement_id)
    return (
        db.query(DesignationControleur)
        .filter(DesignationControleur.etablissement_id == etablissement_id)
        .all()
    )


@router.delete("/controleurs/{designation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoquer_controleur(
    designation_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> None:
    designation = db.get(DesignationControleur, designation_id)
    if designation is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Désignation introuvable.")
    verifier_admin_de_l_etablissement(db, admin, designation.etablissement_id)
    db.delete(designation)
    db.commit()
