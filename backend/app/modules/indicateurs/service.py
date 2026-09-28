"""Lot 7.6 — indicateurs de pilotage (suivi-evaluation du PAG 2021-2026, axe 5 Education).

Tout est recalcule depuis la base a chaque appel (aucun chiffre saisi a la main, aucun
chiffre fige). Protection de la vie privee : toute case qui porterait sur moins de
SEUIL_ANONYMAT eleves est masquee (None), pour qu'on ne puisse pas reconnaitre un eleve
a partir d'un croisement (ex. « 1 fille en Terminale a Karimama »).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.core.territoires import DEPARTEMENTS
from app.modules.alphabetisation.models import InscriptionAlphabetisation
from app.modules.etablissements.models import Classe, Etablissement, StatutEtablissement, TypeEtablissement
from app.modules.evaluations.models import Bulletin
from app.modules.identite.models import Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.messagerie.models import Message
from app.modules.pedagogie.models import Cours, FormatCours
from app.modules.recrutement.models import Contrat, StatutContrat
from app.modules.services_scolaires.models import StatutTicket, TicketCantine, TypeRepasCantine
from app.modules.vie_scolaire.models import EntreeVieScolaire, NatureEntreeVieScolaire

SEUIL_ANONYMAT = 5
SEUIL_REUSSITE = 50.0  # moyenne sur 100 (= 10 sur 20)


@dataclass(frozen=True)
class Perimetre:
    annee_academique: str
    departement: str | None = None
    etablissement_id: str | None = None

    @property
    def libelle(self) -> str:
        if self.etablissement_id:
            return "Établissement"
        return f"Département {self.departement}" if self.departement else "National"


def _bornes_annee(annee_academique: str) -> tuple[date, date]:
    premiere = int(annee_academique.split("-")[0])
    return date(premiere, 9, 1), date(premiere + 1, 8, 31)


def masquer(nombre: int | None) -> int | None:
    """Petits effectifs masques (0 reste affiche : « aucun » ne designe personne)."""
    if nombre is None:
        return None
    return nombre if nombre == 0 or nombre >= SEUIL_ANONYMAT else None


def taux(numerateur: int, denominateur: int) -> float | None:
    if denominateur < SEUIL_ANONYMAT:
        return None
    return round(100 * numerateur / denominateur, 1)


def _filtrer_etablissements(q: Query, p: Perimetre) -> Query:
    if p.etablissement_id:
        return q.filter(Etablissement.id == p.etablissement_id)
    if p.departement:
        return q.filter(Etablissement.departement == p.departement)
    return q


def _inscriptions(db: Session, p: Perimetre) -> Query:
    q = (
        db.query(Inscription)
        .join(Classe, Classe.id == Inscription.classe_id)
        .join(Etablissement, Etablissement.id == Classe.etablissement_id)
        .join(Eleve, Eleve.id == Inscription.eleve_id)
        .filter(Inscription.statut == StatutInscription.VALIDEE, Classe.annee_academique == p.annee_academique)
    )
    return _filtrer_etablissements(q, p)


def _eleves_par_sexe(db: Session, p: Perimetre) -> dict[str | None, int]:
    lignes = (
        _inscriptions(db, p)
        .with_entities(Eleve.sexe, func.count(func.distinct(Eleve.id)))
        .group_by(Eleve.sexe)
        .all()
    )
    return {sexe: n for sexe, n in lignes}


def _reussite(db: Session, p: Perimetre) -> dict:
    q = (
        db.query(Eleve.sexe, Bulletin.moyenne_generale)
        .join(Eleve, Eleve.id == Bulletin.eleve_id)
        .join(Classe, Classe.id == Bulletin.classe_id)
        .join(Etablissement, Etablissement.id == Classe.etablissement_id)
        .filter(Classe.annee_academique == p.annee_academique)
    )
    lignes = _filtrer_etablissements(q, p).all()
    def calcul(filtre):
        retenues = [m for s, m in lignes if filtre(s)]
        return taux(sum(1 for m in retenues if m >= SEUIL_REUSSITE), len(retenues))
    return {
        "bulletins": len(lignes),
        "taux_reussite": calcul(lambda s: True),
        "taux_reussite_filles": calcul(lambda s: s == "F"),
        "taux_reussite_garcons": calcul(lambda s: s == "M"),
    }


def calculer_indicateurs(db: Session, p: Perimetre) -> dict:
    debut, fin = _bornes_annee(p.annee_academique)

    # Etablissements
    etabs = _filtrer_etablissements(db.query(Etablissement), p).all()
    par_type = {t.value: sum(1 for e in etabs if e.type == t) for t in TypeEtablissement}

    # Eleves et parite
    sexes = _eleves_par_sexe(db, p)
    filles, garcons = sexes.get("F", 0), sexes.get("M", 0)
    total_eleves = sum(sexes.values())

    # Assiduite (vie scolaire de l'annee)
    q_vie = (
        db.query(EntreeVieScolaire.nature, func.count(EntreeVieScolaire.id))
        .join(Classe, Classe.id == EntreeVieScolaire.classe_id)
        .join(Etablissement, Etablissement.id == Classe.etablissement_id)
        .filter(EntreeVieScolaire.date_survenue.between(debut, fin))
    )
    vie = dict(_filtrer_etablissements(q_vie, p).group_by(EntreeVieScolaire.nature).all())
    absences = vie.get(NatureEntreeVieScolaire.ABSENCE, 0)

    # Enseignants sous contrat signe et en cours
    q_ens = (
        db.query(func.count(func.distinct(Contrat.enseignant_id)))
        .join(Etablissement, Etablissement.id == Contrat.etablissement_id)
        .filter(Contrat.statut == StatutContrat.SIGNE, Contrat.date_fin >= date.today())
    )
    enseignants = _filtrer_etablissements(q_ens, p).scalar() or 0

    # Cantine (conditions d'etudes ; PAG : loi sur le financement des cantines scolaires)
    q_cantine = (
        db.query(func.count(func.distinct(TicketCantine.utilisateur_id)), func.count(TicketCantine.id))
        .join(TypeRepasCantine, TypeRepasCantine.id == TicketCantine.type_repas_id)
        .join(Etablissement, Etablissement.id == TypeRepasCantine.etablissement_id)
        .filter(TicketCantine.date_service.between(debut, fin), TicketCantine.statut != StatutTicket.REMBOURSE)
    )
    beneficiaires, repas = _filtrer_etablissements(q_cantine, p).one()

    # Inclusion (Lot 7) : cours oraux transcrits, usage des outils d'accessibilite
    q_cours = (
        db.query(Cours.format, Cours.transcription.isnot(None), func.count(Cours.id))
        .join(Classe, Classe.id == Cours.classe_id)
        .join(Etablissement, Etablissement.id == Classe.etablissement_id)
        .filter(Classe.annee_academique == p.annee_academique, Cours.format.in_((FormatCours.AUDIO, FormatCours.VIDEO)))
        .group_by(Cours.format, Cours.transcription.isnot(None))
    )
    lignes_cours = _filtrer_etablissements(q_cours, p).all()
    oraux = sum(n for _, _, n in lignes_cours)
    transcrits = sum(n for _, avec, n in lignes_cours if avec)
    preferences = [
        prefs for (prefs,) in db.query(Utilisateur.preferences_accessibilite).filter(
            Utilisateur.preferences_accessibilite.isnot(None)
        )
    ]
    inclusion = {
        "cours_oraux": oraux,
        "cours_oraux_transcrits": transcrits,
        "taux_transcription": round(100 * transcrits / oraux, 1) if oraux else None,
        # Usage des outils : chiffres nationaux (non rattaches a un etablissement).
        "comptes_mode_ecoute": sum(1 for x in preferences if x.get("mode_ecoute")),
        "comptes_reglages_accessibilite": len(preferences),
        "messages_vocaux": db.query(func.count(Message.id)).filter(Message.audio_lulufiles_id.isnot(None)).scalar() or 0,
        # PAG action 4 : alphabetisation et education des adultes (Lot 7.7).
        "apprenants_alphabetisation": _filtrer_etablissements(
            db.query(func.count(func.distinct(InscriptionAlphabetisation.utilisateur_id)))
            .join(Classe, Classe.id == InscriptionAlphabetisation.classe_id)
            .join(Etablissement, Etablissement.id == Classe.etablissement_id)
            .filter(Classe.annee_academique == p.annee_academique),
            p,
        ).scalar()
        or 0,
    }

    resultat = {
        "annee_academique": p.annee_academique,
        "perimetre": p.libelle,
        "seuil_anonymat": SEUIL_ANONYMAT,
        "etablissements": {
            "total": len(etabs),
            "publics": sum(1 for e in etabs if e.statut == StatutEtablissement.PUBLIC),
            "prives": sum(1 for e in etabs if e.statut == StatutEtablissement.PRIVE),
            "par_type": par_type,
            "sans_territoire": sum(1 for e in etabs if not e.departement),
        },
        "eleves": {
            "total": total_eleves,
            "filles": masquer(filles),
            "garcons": masquer(garcons),
            "sexe_non_renseigne": masquer(sexes.get(None, 0)),
            # Indice de parite filles/garcons (1 = parite ; ODD 4 / PAG).
            "indice_parite": round(filles / garcons, 2) if filles >= SEUIL_ANONYMAT and garcons >= SEUIL_ANONYMAT else None,
        },
        "reussite": _reussite(db, p),
        "assiduite": {
            "absences": absences,
            "retards": vie.get(NatureEntreeVieScolaire.RETARD, 0),
            "absences_par_eleve": round(absences / total_eleves, 2) if total_eleves >= SEUIL_ANONYMAT else None,
        },
        "enseignants": {
            "sous_contrat": enseignants,
            "eleves_par_enseignant": round(total_eleves / enseignants, 1) if enseignants else None,
        },
        "cantine": {"eleves_beneficiaires": masquer(beneficiaires), "repas": repas},
        "inclusion": inclusion,
    }
    if not p.etablissement_id and not p.departement:
        resultat["par_departement"] = [_ligne_departement(db, p, d) for d in DEPARTEMENTS]
    return resultat


def _ligne_departement(db: Session, p: Perimetre, departement: str) -> dict:
    sous = Perimetre(p.annee_academique, departement=departement)
    sexes = _eleves_par_sexe(db, sous)
    filles, garcons = sexes.get("F", 0), sexes.get("M", 0)
    return {
        "departement": departement,
        "etablissements": db.query(func.count(Etablissement.id)).filter(Etablissement.departement == departement).scalar() or 0,
        "eleves": masquer(sum(sexes.values())),
        "filles": masquer(filles),
        "garcons": masquer(garcons),
        "indice_parite": round(filles / garcons, 2) if filles >= SEUIL_ANONYMAT and garcons >= SEUIL_ANONYMAT else None,
        "taux_reussite": _reussite(db, sous)["taux_reussite"],
    }
