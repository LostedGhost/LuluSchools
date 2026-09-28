"""Pastilles du menu : ce qui attend l'utilisateur connecte, par entree de menu.

GET /me/compteurs renvoie {chemin du menu: nombre} (seules les entrees non nulles). Le
menu les affiche en pastille pour qu'aucune action attendue ne passe inapercue :
- A+ / A++ : total de la boite « A traiter » ;
- tuteur : consentements parentaux a donner et depenses a valider (coffre-fort) ;
- enseignant : contrats a signer, copies dont la correction automatique a echoue ;
- eleve : devoirs encore ouverts et pas encore rendus.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.administration.a_traiter import a_traiter
from app.modules.coffre_fort.models import StatutValidationParentale, ValidationParentale
from app.modules.evaluations.models import Devoir, Soumission, StatutSoumission
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.recrutement.models import Contrat, StatutContrat

router = APIRouter(tags=["identite"])


@router.get("/me/compteurs", response_model=dict[str, int])
def mes_compteurs(db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_user)) -> dict[str, int]:
    compteurs: dict[str, int] = {}
    role = utilisateur.role

    if role in (RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL):
        total = sum(s.nombre for s in a_traiter(db=db, admin=utilisateur))
        prefixe = "/admin-ministeriel" if role == RoleUtilisateur.ADMIN_MINISTERIEL else "/admin-etablissement"
        compteurs[f"{prefixe}/a-traiter"] = total

    elif role == RoleUtilisateur.TUTEUR:
        consentements = (
            db.query(func.count(Inscription.id))
            .join(Eleve, Eleve.id == Inscription.eleve_id)
            .filter(Eleve.tuteur_id == utilisateur.id, Inscription.statut == StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL)
            .scalar()
        )
        validations = (
            db.query(func.count(ValidationParentale.id))
            .filter(ValidationParentale.tuteur_id == utilisateur.id, ValidationParentale.statut == StatutValidationParentale.EN_ATTENTE)
            .scalar()
        )
        compteurs["/tuteur"] = consentements + validations

    elif role == RoleUtilisateur.ENSEIGNANT:
        compteurs["/enseignant/contrats"] = (
            db.query(func.count(Contrat.id))
            .filter(Contrat.enseignant_id == utilisateur.id, Contrat.statut == StatutContrat.EN_ATTENTE_SIGNATURE)
            .scalar()
        )
        compteurs["/enseignant/devoirs"] = (
            db.query(func.count(Soumission.id))
            .join(Devoir, Devoir.id == Soumission.devoir_id)
            .filter(Devoir.enseignant_id == utilisateur.id, Soumission.statut == StatutSoumission.ECHEC_CORRECTION)
            .scalar()
        )

    elif role == RoleUtilisateur.ELEVE:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
        if eleve is not None:
            classes = [c for (c,) in db.query(Inscription.classe_id).filter(
                Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)]
            if classes:
                rendus = db.query(Soumission.devoir_id).filter(Soumission.eleve_id == eleve.id)
                compteurs["/eleve/devoirs"] = (
                    db.query(func.count(Devoir.id))
                    .filter(
                        Devoir.classe_id.in_(classes),
                        Devoir.date_limite > datetime.now(timezone.utc),
                        Devoir.masque_le.is_(None),
                        Devoir.id.notin_(rendus),
                    )
                    .scalar()
                )

    return {cle: n for cle, n in compteurs.items() if n}
