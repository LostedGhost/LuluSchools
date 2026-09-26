from sqlalchemy.orm import Session

from app.modules.audit.models import JournalAuditMinisteriel
from app.modules.identite.models import RoleUtilisateur, Utilisateur


def journaliser_action_ministerielle(
    db: Session,
    acteur: Utilisateur,
    action: str,
    cible_type: str,
    cible_id: str,
    motif: str | None = None,
) -> None:
    """Point d'entree UNIQUE pour ecrire dans JournalAuditMinisteriel (UC-36/51) - jamais
    construit a la main dans un router. N'accepte que l'acteur ADMIN_MINISTERIEL : ce
    journal couvre le mandat ministeriel, pas les actions d'un A+ (voir cahier des
    charges, risque R3). N'effectue PAS le commit : appele avant le commit de l'action
    elle-meme pour que l'ecriture d'audit et l'action restent dans la meme transaction
    (jamais une action sans sa trace, ni une trace sans l'action qui l'a produite)."""
    if acteur.role != RoleUtilisateur.ADMIN_MINISTERIEL:
        return
    db.add(
        JournalAuditMinisteriel(
            acteur_id=acteur.id,
            action=action,
            cible_type=cible_type,
            cible_id=cible_id,
            motif=motif,
        )
    )
