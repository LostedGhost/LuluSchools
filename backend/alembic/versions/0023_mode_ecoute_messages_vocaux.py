"""Lot 7.4 : messages vocaux (mode Ecoute)

Revision ID: 0023_messages_vocaux
Revises: 0022_transcriptions_cours
Create Date: 2026-09-29 00:30:00

"""
from alembic import op


revision = '0023_messages_vocaux'
down_revision = '0022_transcriptions_cours'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS audio_lulufiles_id VARCHAR(36)")
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS duree_audio_s INTEGER")


def downgrade() -> None:
    op.drop_column('messages', 'duree_audio_s')
    op.drop_column('messages', 'audio_lulufiles_id')
