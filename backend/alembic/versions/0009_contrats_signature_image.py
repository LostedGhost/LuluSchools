"""contrats : signature_image_lulufiles_id (signature dessinee, remplace le nom tape)

Revision ID: 0009_contrats_signature_image
Revises: 0008_pedagogie_evaluations_actes
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0009_contrats_signature_image"
down_revision = "0008_pedagogie_evaluations_actes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contrats", sa.Column("signature_image_lulufiles_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column("contrats", "signature_image_lulufiles_id")
