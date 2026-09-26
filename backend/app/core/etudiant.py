from sqlalchemy.orm import Session

from app.modules.etablissements.models import Classe, Etablissement, TypeEtablissement
from app.modules.inscriptions.models import Inscription, StatutInscription


def est_etudiant(db: Session, eleve_id: str) -> bool:
    """UC-42/57/58 (lot admin etablissement) : "etudiant" n'est jamais un role separe -
    derive du type d'etablissement (UP) de la derniere inscription VALIDEE de l'eleve.
    Point d'entree UNIQUE, reutilise par la vie scolaire (etablissements/router.py), les
    micro-jobs (micro_jobs/router.py) et la marketplace (marketplace/router.py) - jamais
    duplique. `eleve_id` est l'id de la table Eleve (pas Utilisateur.id)."""
    inscription = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve_id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )
    if inscription is None:
        return False
    classe = db.get(Classe, inscription.classe_id)
    etablissement = db.get(Etablissement, classe.etablissement_id)
    return etablissement.type == TypeEtablissement.UP
