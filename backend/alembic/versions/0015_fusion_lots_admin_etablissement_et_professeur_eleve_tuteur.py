"""fusion lot admin etablissement et lot professeur eleve tuteur

Migration de fusion pure (pas de DDL) : les deux lots ont ete developpes en parallele
sur deux branches distinctes a partir du meme point commun (0005_affectation_enseignant),
chacune sans connaissance de l'autre - `0007_admin_etab` (admin etablissement, UC-39 a
UC-58) et `0014_el_professor_famille` (volet Professeur/Eleve/Tuteur, UC-23 a UC-38)
etaient donc deux HEADS Alembic distincts apres la fusion git. Sans cette migration,
`alembic upgrade head` (et `seed_mega.py::reset_schema()`, qui appelle
`command.stamp(alembic_cfg, "head", purge=True)`) echoue avec
`Multiple head revisions are present`. Aucun chevauchement de schema entre les deux
lots (verifie table par table) - une fusion, jamais un merge de contenu.

Revision ID: 0015_fusion_lots
Revises: 0007_admin_etab, 0014_el_professor_famille
Create Date: 2026-09-26 22:38:32.782838

"""
from alembic import op
import sqlalchemy as sa


revision = '0015_fusion_lots'
down_revision = ('0007_admin_etab', '0014_el_professor_famille')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
