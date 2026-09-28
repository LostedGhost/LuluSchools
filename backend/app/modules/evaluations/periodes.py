"""Periodes d'evaluation d'une annee academique (bulletins).

[Delegue] Decoupage retenu pour l'annee « AAAA-BBBB » (rentree en septembre au Benin) :
- primaire et secondaire (EP, ES) : trois trimestres - 1er sept.-31 dec., 1er janv.-31 mars,
  1er avril-31 aout ;
- universites et poles superieurs (UP) : deux semestres - 1er sept.-31 janv., 1er fev.-31 aout.
Un devoir appartient a la periode qui contient sa date limite ; le bulletin d'une periode ne
tient compte que de ses devoirs (auparavant, toutes les periodes affichaient la meme moyenne).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from app.modules.etablissements.models import TypeEtablissement


@dataclass(frozen=True)
class Periode:
    code: str
    libelle: str
    debut: date
    fin: date  # inclus


# (code, libelle, (mois, jour) de debut, (mois, jour) de fin)
_TRIMESTRES = (
    ("trimestre1", "1er trimestre", (9, 1), (12, 31)),
    ("trimestre2", "2e trimestre", (1, 1), (3, 31)),
    ("trimestre3", "3e trimestre", (4, 1), (8, 31)),
)
_SEMESTRES = (
    ("semestre1", "1er semestre", (9, 1), (1, 31)),
    ("semestre2", "2e semestre", (2, 1), (8, 31)),
)
CODES = {c for c, *_ in _TRIMESTRES + _SEMESTRES}


def _annee_de(annee_academique: str, mois: int) -> int:
    """Septembre-decembre : premiere annee ; janvier-aout : seconde."""
    premiere = int(annee_academique.split("-")[0])
    return premiere if mois >= 9 else premiere + 1


def periodes(type_etablissement: TypeEtablissement, annee_academique: str) -> list[Periode]:
    modele = _SEMESTRES if type_etablissement == TypeEtablissement.UP else _TRIMESTRES
    return [
        Periode(code, libelle, date(_annee_de(annee_academique, md[0]), *md), date(_annee_de(annee_academique, mf[0]), *mf))
        for code, libelle, md, mf in modele
    ]


def trouver(type_etablissement: TypeEtablissement, annee_academique: str, code: str) -> Periode | None:
    return next((p for p in periodes(type_etablissement, annee_academique) if p.code == code), None)


def bornes_utc(periode: Periode) -> tuple[datetime, datetime]:
    debut = datetime.combine(periode.debut, time.min, tzinfo=timezone.utc)
    return debut, datetime.combine(periode.fin + timedelta(days=1), time.min, tzinfo=timezone.utc)


def periode_de(moment: datetime, type_etablissement: TypeEtablissement, annee_academique: str) -> Periode:
    """Periode contenant `moment` ; avant la rentree -> la premiere, apres la fin -> la derniere."""
    jour = (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).date()
    liste = periodes(type_etablissement, annee_academique)
    if jour < liste[0].debut:
        return liste[0]
    return next((p for p in liste if p.debut <= jour <= p.fin), liste[-1])
