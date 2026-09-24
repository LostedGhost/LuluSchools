"""contrats : date_fin (necessaire pour la fenetre de reconduction UC-05b)

Revision ID: 0007_contrats_date_fin
Revises: 0006_recrutement
Create Date: 2026-09-24

"""
import sqlalchemy as sa
from alembic import op

revision = "0007_contrats_date_fin"
down_revision = "0006_recrutement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contrats", sa.Column("date_fin", sa.Date(), nullable=True))
    op.execute("UPDATE contrats SET date_fin = CURRENT_DATE + INTERVAL '1 year' WHERE date_fin IS NULL")
    op.alter_column("contrats", "date_fin", nullable=False)


def downgrade() -> None:
    op.drop_column("contrats", "date_fin")
