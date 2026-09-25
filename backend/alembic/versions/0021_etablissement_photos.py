"""etablissement_photos (annuaire public / vitrine)

Revision ID: 0021_etablissement_photos
Revises: 0020_micro_jobs
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0021_etablissement_photos"
down_revision = "0020_micro_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "etablissement_photos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False),
        sa.Column("lulufiles_file_id", sa.String(length=100), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_etablissement_photos_etablissement_id",
        "etablissement_photos",
        ["etablissement_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_etablissement_photos_etablissement_id", table_name="etablissement_photos")
    op.drop_table("etablissement_photos")
