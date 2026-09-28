"""Lot 7.7 : centres d'alphabetisation (type CA) et inscriptions des adultes

Revision ID: 0025_alphabetisation
Revises: 0024_territoires_parite
Create Date: 2026-09-29 03:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0025_alphabetisation'
down_revision = '0024_territoires_parite'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADD VALUE ne peut pas s'executer dans la transaction d'une migration (PostgreSQL).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE typeetablissement ADD VALUE IF NOT EXISTS 'CA'")
    op.create_table(
        'inscriptions_alphabetisation',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column('classe_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['classe_id'], ['classes.id']),
        sa.ForeignKeyConstraint(['utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('utilisateur_id', 'classe_id', name='uq_alphabetisation_utilisateur_classe'),
        if_not_exists=True,
    )
    op.create_index('ix_inscriptions_alphabetisation_utilisateur_id', 'inscriptions_alphabetisation', ['utilisateur_id'], if_not_exists=True)
    op.create_index('ix_inscriptions_alphabetisation_classe_id', 'inscriptions_alphabetisation', ['classe_id'], if_not_exists=True)


def downgrade() -> None:
    # Une valeur d'enum PostgreSQL ne se retire pas : 'CA' reste declaree, sans usage.
    op.drop_table('inscriptions_alphabetisation')
