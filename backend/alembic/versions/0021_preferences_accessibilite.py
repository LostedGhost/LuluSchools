"""Lot 7.2 : preferences d'accessibilite synchronisees sur le compte

Revision ID: 0021_preferences_accessibilite
Revises: 0020_saisie_papier
Create Date: 2026-09-28 22:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0021_preferences_accessibilite'
down_revision = '0020_saisie_papier'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # if_not_exists : rejouable sur une base construite par create_all puis estampillee (cf. 0017).
    op.execute("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS preferences_accessibilite JSON")


def downgrade() -> None:
    op.drop_column('utilisateurs', 'preferences_accessibilite')
