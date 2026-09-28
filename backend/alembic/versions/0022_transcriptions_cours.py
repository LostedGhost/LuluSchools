"""Lot 7.3 : transcription et sous-titres des cours audio et video

Revision ID: 0022_transcriptions_cours
Revises: 0021_preferences_accessibilite
Create Date: 2026-09-28 23:00:00

"""
from alembic import op


revision = '0022_transcriptions_cours'
down_revision = '0021_preferences_accessibilite'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE cours ADD COLUMN IF NOT EXISTS transcription TEXT")
    op.execute("ALTER TABLE cours ADD COLUMN IF NOT EXISTS sous_titres_vtt TEXT")


def downgrade() -> None:
    op.drop_column('cours', 'sous_titres_vtt')
    op.drop_column('cours', 'transcription')
