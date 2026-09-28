from sqlalchemy.orm import Session

from app.modules.alphabetisation.models import InscriptionAlphabetisation


def est_apprenant_de_la_classe(db: Session, utilisateur_id: str, classe_id: str) -> bool:
    return (
        db.query(InscriptionAlphabetisation.id)
        .filter(InscriptionAlphabetisation.utilisateur_id == utilisateur_id, InscriptionAlphabetisation.classe_id == classe_id)
        .first()
        is not None
    )
