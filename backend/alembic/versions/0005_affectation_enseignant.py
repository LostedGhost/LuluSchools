"""affectation_enseignant - lien enseignant <-> classe precise

Revision ID: 0005_affectation_enseignant
Revises: 0004_marketplace
Create Date: 2026-09-26

Constat d'audit RBAC : le seul lien enseignant<->etablissement etait Contrat (portee
etablissement entier), donc n'importe quel enseignant sous contrat signe pouvait gerer
les cours/quiz/devoirs/sessions live de N'IMPORTE QUELLE classe de son etablissement,
pas seulement les siennes. Cette table devient le vrai filtre de portee pour ces
actions - voir app/modules/etablissements/models.py::AffectationEnseignant.
"""
from alembic import op
import sqlalchemy as sa


revision = '0005_affectation_enseignant'
down_revision = '0004_marketplace'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'affectations_enseignant',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('enseignant_id', sa.String(length=36), nullable=False),
        sa.Column('classe_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enseignant_id'], ['utilisateurs.id']),
        sa.ForeignKeyConstraint(['classe_id'], ['classes.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('enseignant_id', 'classe_id', name='uq_affectation_enseignant_classe'),
    )
    op.create_index(
        op.f('ix_affectations_enseignant_enseignant_id'), 'affectations_enseignant', ['enseignant_id']
    )
    op.create_index(
        op.f('ix_affectations_enseignant_classe_id'), 'affectations_enseignant', ['classe_id']
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_affectations_enseignant_classe_id'), table_name='affectations_enseignant')
    op.drop_index(op.f('ix_affectations_enseignant_enseignant_id'), table_name='affectations_enseignant')
    op.drop_table('affectations_enseignant')
