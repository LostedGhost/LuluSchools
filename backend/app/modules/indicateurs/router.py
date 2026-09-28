"""Lot 7.6 : GET /admin/indicateurs (+ export CSV) — pilotage du ministere (A++) et de
chaque etablissement (A+, limite au sien)."""

import csv
import io

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.core.territoires import DEPARTEMENTS
from app.modules.etablissements.models import AdminEtablissement, annee_academique_courante
from app.modules.identite.models import RoleUtilisateur, Utilisateur
from app.modules.indicateurs.service import Perimetre, calculer_indicateurs

router = APIRouter(tags=["indicateurs"])

_ADMINS = require_roles(RoleUtilisateur.ADMIN_MINISTERIEL, RoleUtilisateur.ADMIN_ETABLISSEMENT)


def _perimetre(
    db: Session, utilisateur: Utilisateur, annee_academique: str | None, departement: str | None, etablissement_id: str | None
) -> Perimetre:
    annee = annee_academique or annee_academique_courante()
    if departement is not None and departement not in DEPARTEMENTS:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "departement_inconnu", "Département inconnu.")
    if utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        # L'A+ ne voit que son etablissement, quel que soit le filtre demande.
        lien = db.get(AdminEtablissement, utilisateur.id)
        if lien is None:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Aucun établissement administré.")
        return Perimetre(annee, etablissement_id=lien.etablissement_id)
    return Perimetre(annee, departement=departement, etablissement_id=etablissement_id)


@router.get("/admin/indicateurs")
def indicateurs(
    annee_academique: str | None = Query(default=None, pattern=r"^\d{4}-\d{4}$"),
    departement: str | None = None,
    etablissement_id: str | None = None,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(_ADMINS),
) -> dict:
    return calculer_indicateurs(db, _perimetre(db, utilisateur, annee_academique, departement, etablissement_id))


def _aplatir(prefixe: str, valeur, lignes: list[tuple[str, object]]) -> None:
    if isinstance(valeur, dict):
        for cle, sous in valeur.items():
            _aplatir(f"{prefixe}.{cle}" if prefixe else cle, sous, lignes)
    elif not isinstance(valeur, list):
        lignes.append((prefixe, "" if valeur is None else valeur))


@router.get("/admin/indicateurs.csv")
def exporter_indicateurs(
    annee_academique: str | None = Query(default=None, pattern=r"^\d{4}-\d{4}$"),
    departement: str | None = None,
    etablissement_id: str | None = None,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(_ADMINS),
) -> Response:
    """Export tableur (separateur « ; », ouvrable tel quel dans Excel en francais)."""
    donnees = calculer_indicateurs(db, _perimetre(db, utilisateur, annee_academique, departement, etablissement_id))
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";")
    ecrivain.writerow(["indicateur", "valeur"])
    lignes: list[tuple[str, object]] = []
    _aplatir("", {k: v for k, v in donnees.items() if k != "par_departement"}, lignes)
    ecrivain.writerows(lignes)
    if "par_departement" in donnees:
        ecrivain.writerow([])
        colonnes = list(donnees["par_departement"][0].keys())
        ecrivain.writerow(colonnes)
        for ligne in donnees["par_departement"]:
            ecrivain.writerow(["" if ligne[c] is None else ligne[c] for c in colonnes])
    nom = f"indicateurs-luluschools-{donnees['annee_academique']}.csv"
    return Response(
        content="\ufeff" + tampon.getvalue(),  # BOM : accents corrects dans Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )
