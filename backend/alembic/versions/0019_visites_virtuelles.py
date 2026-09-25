"""visites_virtuelles (UC-19)

Revision ID: 0019_visites_virtuelles
Revises: 0018_cours_direct
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0019_visites_virtuelles"
down_revision = "0018_cours_direct"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visites_virtuelles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
        sa.Column("type", sa.Enum("TROIS_D", "DRONE", name="typevisitevirtuelle"), nullable=False),
        sa.Column("lien_externe", sa.Text(), nullable=False),
        sa.Column("attestation_autorisation", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_visites_virtuelles_etablissement_id", "visites_virtuelles", ["etablissement_id"])


def downgrade() -> None:
    op.drop_index("ix_visites_virtuelles_etablissement_id", table_name="visites_virtuelles")
    op.drop_table("visites_virtuelles")
