"""Lot 7.5 (UC-80) : memoire des requetes rejouees depuis la file d'attente hors ligne

Revision ID: 0027_requetes_idempotentes
Revises: 0026_eftp_stages_bourses
Create Date: 2026-09-29 05:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0027_requetes_idempotentes'
down_revision = '0026_eftp_stages_bourses'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'requetes_idempotentes',
        sa.Column('empreinte', sa.String(length=64), nullable=False),
        sa.Column('statut_http', sa.Integer(), nullable=False),
        sa.Column('type_contenu', sa.String(length=100), nullable=False),
        sa.Column('corps', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('empreinte'),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table('requetes_idempotentes')
