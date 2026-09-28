"""Lot 7.6 : departement et commune des etablissements, sexe des eleves (indicateurs)

Revision ID: 0024_territoires_parite
Revises: 0023_messages_vocaux
Create Date: 2026-09-29 01:30:00

"""
from alembic import op


revision = '0024_territoires_parite'
down_revision = '0023_messages_vocaux'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE etablissements ADD COLUMN IF NOT EXISTS departement VARCHAR(30)")
    op.execute("ALTER TABLE etablissements ADD COLUMN IF NOT EXISTS commune VARCHAR(60)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_etablissements_departement ON etablissements (departement)")
    op.execute("ALTER TABLE eleves ADD COLUMN IF NOT EXISTS sexe VARCHAR(1)")


def downgrade() -> None:
    op.drop_column('eleves', 'sexe')
    op.drop_index('ix_etablissements_departement', table_name='etablissements')
    op.drop_column('etablissements', 'commune')
    op.drop_column('etablissements', 'departement')
