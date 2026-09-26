"""resume asynchrone de session live (tuteur)

Revision ID: 0013_resume_session_live
Revises: 0012_coffre_fort_familial
Create Date: 2026-09-26

UC-33.1 : a la cloture d'une session live, un resume texte est genere par FreeLLM a
partir du chat + du contenu textuel du tableau, et rendu disponible au tuteur des
eleves ayant participe (UC-33.2 : jamais d'observation en direct).
"""
from alembic import op
import sqlalchemy as sa


revision = '0013_resume_session_live'
down_revision = '0012_coffre_fort_familial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'resumes_session_live',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('contenu', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_live.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id'),
    )
    op.create_index(op.f('ix_resumes_session_live_session_id'), 'resumes_session_live', ['session_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_resumes_session_live_session_id'), table_name='resumes_session_live')
    op.drop_table('resumes_session_live')
