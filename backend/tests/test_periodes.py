"""Periodes d'evaluation : trimestres (EP/ES), semestres (UP) et bulletin limite a sa periode."""

from datetime import date, datetime, timezone

from app.core.security import decode_token
from app.modules.etablissements.models import TypeEtablissement
from app.modules.evaluations import periodes


def test_trimestres_et_semestres():
    t = periodes.periodes(TypeEtablissement.ES, "2026-2027")
    assert [(p.code, p.debut, p.fin) for p in t] == [
        ("trimestre1", date(2026, 9, 1), date(2026, 12, 31)),
        ("trimestre2", date(2027, 1, 1), date(2027, 3, 31)),
        ("trimestre3", date(2027, 4, 1), date(2027, 8, 31)),
    ]
    s = periodes.periodes(TypeEtablissement.UP, "2026-2027")
    assert [(p.code, p.debut, p.fin) for p in s] == [
        ("semestre1", date(2026, 9, 1), date(2027, 1, 31)),
        ("semestre2", date(2027, 2, 1), date(2027, 8, 31)),
    ]
    assert periodes.trouver(TypeEtablissement.UP, "2026-2027", "trimestre1") is None


def test_periode_d_une_date():
    def code(jour, type_etab=TypeEtablissement.ES):
        return periodes.periode_de(datetime(*jour, tzinfo=timezone.utc), type_etab, "2026-2027").code

    assert code((2026, 12, 31)) == "trimestre1"
    assert code((2027, 1, 1)) == "trimestre2"
    assert code((2027, 1, 20), TypeEtablissement.UP) == "semestre1"
    assert code((2026, 7, 1)) == "trimestre1"  # avant la rentree : premiere periode
    assert code((2027, 10, 1)) == "trimestre3"  # apres la fin d'annee : derniere periode


def test_periodes_de_la_classe_et_periode_inconnue(client, classe_avec_enseignant_et_eleve):
    ctx = classe_avec_enseignant_et_eleve
    liste = client.get(f"/api/v1/classes/{ctx['classe']['id']}/periodes", headers=ctx["admin_headers"]).json()
    assert len(liste) in (2, 3) and sum(p["courante"] for p in liste) == 1
    eleve = decode_token(ctx["eleve_headers"]["Authorization"].split(" ")[1])["sub"]
    refus = client.get(
        f"/api/v1/eleves/{eleve}/bulletins",
        params={"classe_id": ctx["classe"]["id"], "periode": "annee"},
        headers=ctx["admin_headers"],
    )
    assert refus.status_code == 422 and refus.json()["error"]["code"] == "periode_invalide"
