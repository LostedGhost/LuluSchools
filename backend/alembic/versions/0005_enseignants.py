"""enseignants

Revision ID: 0005_enseignants
Revises: 0004_inscriptions
Create Date: 2026-09-24

"""
import sqlalchemy as sa
from alembic import op

revision = "0005_enseignants"
down_revision = "0004_inscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enseignants",
        sa.Column(
            "utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), primary_key=True
        ),
    )


def downgrade() -> None:
    op.drop_table("enseignants")
