from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.modules.coffre_fort.models import PlafondFamilial
from app.modules.coffre_fort.service import construire_releve_financier
from app.modules.cours_direct.models import ParticipationLive, SessionLive
from app.modules.evaluations.models import Devoir, Soumission, StatutSoumission
from app.modules.inscriptions.models import Eleve
from app.modules.vie_scolaire.models import EntreeVieScolaire


def _periode_par_defaut() -> tuple[date, date]:
    fin = date.today()
    return fin - timedelta(days=7), fin


def construire_sources_radar_familial(
    db: Session, eleve_utilisateur_id: str, *, debut: date | None, fin: date | None
) -> list[str]:
    """UC-36.1/36.2 : chaque ligne est un fait deja etabli ailleurs sur la plateforme,
    date et source, jamais une reformulation ou une inference - c'est cette liste,
    et uniquement elle, que FreeLLM recoit pour rediger le digest narratif (voir
    FreeLLMClient.generer_digest_famille), garantissant que le resume reste tracable."""
    if debut is None or fin is None:
        debut_defaut, fin_defaut = _periode_par_defaut()
        debut = debut or debut_defaut
        fin = fin or fin_defaut

    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        return []

    sources: list[str] = []

    entrees = (
        db.query(EntreeVieScolaire)
        .filter(
            EntreeVieScolaire.eleve_id == eleve.id,
            EntreeVieScolaire.date_survenue >= debut,
            EntreeVieScolaire.date_survenue <= fin,
        )
        .order_by(EntreeVieScolaire.date_survenue.asc())
        .all()
    )
    for entree in entrees:
        matiere = f" ({entree.matiere})" if entree.matiere else ""
        sources.append(
            f"Vie scolaire du {entree.date_survenue.isoformat()} : {entree.nature.value}{matiere} - {entree.description}"
        )

    soumissions = (
        db.query(Soumission)
        .join(Devoir, Devoir.id == Soumission.devoir_id)
        .filter(
            Soumission.eleve_id == eleve.id,
            Soumission.statut == StatutSoumission.CORRIGEE,
        )
        .all()
    )
    for soumission in soumissions:
        jour = soumission.created_at.date()
        if not (debut <= jour <= fin):
            continue
        devoir = db.get(Devoir, soumission.devoir_id)
        matiere = devoir.matiere if devoir is not None else "matière inconnue"
        titre = devoir.titre if devoir is not None else ""
        note = f"{soumission.note:g}" if soumission.note is not None else "non notée"
        sources.append(f"Devoir de {matiere} \"{titre}\" corrige le {jour.isoformat()} : note {note}")

    participations = (
        db.query(ParticipationLive).filter(ParticipationLive.eleve_utilisateur_id == eleve_utilisateur_id).all()
    )
    for participation in participations:
        jour = participation.created_at.date()
        if not (debut <= jour <= fin):
            continue
        session_live = db.get(SessionLive, participation.session_id)
        date_session = session_live.date_heure.date().isoformat() if session_live is not None else jour.isoformat()
        sources.append(f"Session live suivie le {date_session}")

    plafond = db.query(PlafondFamilial).filter(PlafondFamilial.eleve_utilisateur_id == eleve_utilisateur_id).first()
    if plafond is not None:
        releve = construire_releve_financier(db, eleve_utilisateur_id, debut=debut, fin=fin)
        if releve["solde_net"] != 0:
            sources.append(
                f"Activité financière du {debut.isoformat()} au {fin.isoformat()} : solde net {releve['solde_net']:g} FCFA"
            )

    return sources
