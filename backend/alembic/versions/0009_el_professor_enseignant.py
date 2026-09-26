"""el professor - volet enseignant + alertes de securite

Revision ID: 0009_el_professor_enseignant
Revises: 0008_evaluations_enrichies
Create Date: 2026-09-26

UC-27 : conseil educatif/moral/professionnel pour l'enseignant (distinct du fil
eleve<->cours deja existant). Garde-fou de securite (UC-27.3) : une alerte est
preparee pour l'administration quand la question contient un signal de danger, voir
pedagogie/router.py::_detecter_signal_alerte.
"""
from alembic import op
import sqlalchemy as sa


revision = '0009_el_professor_enseignant'
down_revision = '0008_evaluations_enrichies'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sessions_el_professor_enseignant',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('enseignant_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=True),
        sa.Column('sujet', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enseignant_id'], ['enseignants.utilisateur_id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_sessions_el_professor_enseignant_enseignant_id'),
        'sessions_el_professor_enseignant', ['enseignant_id'],
    )
    op.create_index(
        op.f('ix_sessions_el_professor_enseignant_eleve_utilisateur_id'),
        'sessions_el_professor_enseignant', ['eleve_utilisateur_id'],
    )

    op.create_table(
        'messages_el_professor_enseignant',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.Enum('ENSEIGNANT', 'ASSISTANT', name='rolemessageelprofessorenseignant'), nullable=False),
        sa.Column('contenu', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_el_professor_enseignant.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_messages_el_professor_enseignant_session_id'), 'messages_el_professor_enseignant', ['session_id']
    )

    op.create_table(
        'alertes_el_professor',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('etablissement_id', sa.String(length=36), nullable=True),
        sa.Column('motif', sa.Text(), nullable=False),
        sa.Column('traite', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('traite_par_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_el_professor_enseignant.id']),
        sa.ForeignKeyConstraint(['etablissement_id'], ['etablissements.id']),
        sa.ForeignKeyConstraint(['traite_par_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_alertes_el_professor_session_id'), 'alertes_el_professor', ['session_id'])
    op.create_index(op.f('ix_alertes_el_professor_etablissement_id'), 'alertes_el_professor', ['etablissement_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_alertes_el_professor_etablissement_id'), table_name='alertes_el_professor')
    op.drop_index(op.f('ix_alertes_el_professor_session_id'), table_name='alertes_el_professor')
    op.drop_table('alertes_el_professor')

    op.drop_index(op.f('ix_messages_el_professor_enseignant_session_id'), table_name='messages_el_professor_enseignant')
    op.drop_table('messages_el_professor_enseignant')
    sa.Enum(name='rolemessageelprofessorenseignant').drop(op.get_bind(), checkfirst=True)

    op.drop_index(
        op.f('ix_sessions_el_professor_enseignant_eleve_utilisateur_id'),
        table_name='sessions_el_professor_enseignant',
    )
    op.drop_index(
        op.f('ix_sessions_el_professor_enseignant_enseignant_id'), table_name='sessions_el_professor_enseignant'
    )
    op.drop_table('sessions_el_professor_enseignant')
