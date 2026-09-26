"""vie_scolaire - absences, retards, appreciations, incidents

Revision ID: 0007_vie_scolaire
Revises: 0006_annee_academique
Create Date: 2026-09-26

UC-23 : historique immuable (pas de PATCH/DELETE expose) - une entree consignee par un
enseignant de matiere n'est visible que par lui (portee "sa matiere"), le professeur
principal et l'administration voient tout (voir app/modules/vie_scolaire/router.py).
"""
from alembic import op
import sqlalchemy as sa


revision = '0007_vie_scolaire'
down_revision = '0006_annee_academique'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'entrees_vie_scolaire',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('eleve_id', sa.String(length=36), nullable=False),
        sa.Column('classe_id', sa.String(length=36), nullable=False),
        sa.Column('auteur_id', sa.String(length=36), nullable=False),
        sa.Column(
            'nature',
            sa.Enum('ABSENCE', 'RETARD', 'APPRECIATION', 'INCIDENT', 'FELICITATION', name='nature_entree_vie_scolaire'),
            nullable=False,
        ),
        sa.Column('matiere', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('date_survenue', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['eleve_id'], ['eleves.id']),
        sa.ForeignKeyConstraint(['classe_id'], ['classes.id']),
        sa.ForeignKeyConstraint(['auteur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_entrees_vie_scolaire_eleve_id'), 'entrees_vie_scolaire', ['eleve_id'])
    op.create_index(op.f('ix_entrees_vie_scolaire_classe_id'), 'entrees_vie_scolaire', ['classe_id'])
    op.create_index(op.f('ix_entrees_vie_scolaire_auteur_id'), 'entrees_vie_scolaire', ['auteur_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_entrees_vie_scolaire_auteur_id'), table_name='entrees_vie_scolaire')
    op.drop_index(op.f('ix_entrees_vie_scolaire_classe_id'), table_name='entrees_vie_scolaire')
    op.drop_index(op.f('ix_entrees_vie_scolaire_eleve_id'), table_name='entrees_vie_scolaire')
    op.drop_table('entrees_vie_scolaire')
    sa.Enum(name='nature_entree_vie_scolaire').drop(op.get_bind(), checkfirst=True)
