"""tableau collaboratif, permissions de craie, chat de session live

Revision ID: 0010_tableau_collaboratif
Revises: 0009_el_professor_enseignant
Create Date: 2026-09-26

UC-25 : sessions live v2 - tableau collaboratif ("craie/chiffon"), file de demandes de
craie, permissions d'ecriture revocables a tout instant, captures automatiques a la
cloture, chat de session (salle sociale pre-cours incluse). Le flux audio/video reel
(signalisation WebRTC mesh, voir cours_direct/router.py) ne cree aucune table : c'est un
canal WebSocket en memoire, rien a persister au-dela des tables ci-dessous.
"""
from alembic import op
import sqlalchemy as sa


revision = '0010_tableau_collaboratif'
down_revision = '0009_el_professor_enseignant'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'panneaux_tableau',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('ordre', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_live.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_panneaux_tableau_session_id'), 'panneaux_tableau', ['session_id'])

    op.create_table(
        'traits_tableau',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('panneau_id', sa.String(length=36), nullable=False),
        sa.Column('auteur_id', sa.String(length=36), nullable=False),
        sa.Column('type', sa.Enum('TRAIT_LIBRE', 'TEXTE', 'EFFACEMENT', name='typetraittableau'), nullable=False),
        sa.Column('donnees', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['panneau_id'], ['panneaux_tableau.id']),
        sa.ForeignKeyConstraint(['auteur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_traits_tableau_panneau_id'), 'traits_tableau', ['panneau_id'])
    op.create_index(op.f('ix_traits_tableau_auteur_id'), 'traits_tableau', ['auteur_id'])

    op.create_table(
        'permissions_ecriture_tableau',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column('mode', sa.Enum('PRETEE', 'ACCORDEE', name='modepermissionecriture'), nullable=False),
        sa.Column('accordee_par_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_live.id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.ForeignKeyConstraint(['accordee_par_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'eleve_utilisateur_id', name='uq_permission_ecriture_tableau'),
    )
    op.create_index(
        op.f('ix_permissions_ecriture_tableau_session_id'), 'permissions_ecriture_tableau', ['session_id']
    )
    op.create_index(
        op.f('ix_permissions_ecriture_tableau_eleve_utilisateur_id'),
        'permissions_ecriture_tableau', ['eleve_utilisateur_id'],
    )

    op.create_table(
        'demandes_craie',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column(
            'statut', sa.Enum('EN_ATTENTE', 'ACCORDEE', 'REFUSEE', name='statutdemandecraie'),
            nullable=False, server_default='EN_ATTENTE',
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_live.id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_demandes_craie_session_id'), 'demandes_craie', ['session_id'])
    op.create_index(op.f('ix_demandes_craie_eleve_utilisateur_id'), 'demandes_craie', ['eleve_utilisateur_id'])

    op.create_table(
        'captures_tableau_session',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('panneau_id', sa.String(length=36), nullable=False),
        sa.Column('lulufiles_file_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_live.id']),
        sa.ForeignKeyConstraint(['panneau_id'], ['panneaux_tableau.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_captures_tableau_session_session_id'), 'captures_tableau_session', ['session_id'])
    op.create_index(op.f('ix_captures_tableau_session_panneau_id'), 'captures_tableau_session', ['panneau_id'])

    op.create_table(
        'messages_session_live',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('auteur_id', sa.String(length=36), nullable=False),
        sa.Column('contenu', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_live.id']),
        sa.ForeignKeyConstraint(['auteur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_messages_session_live_session_id'), 'messages_session_live', ['session_id'])
    op.create_index(op.f('ix_messages_session_live_auteur_id'), 'messages_session_live', ['auteur_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_messages_session_live_auteur_id'), table_name='messages_session_live')
    op.drop_index(op.f('ix_messages_session_live_session_id'), table_name='messages_session_live')
    op.drop_table('messages_session_live')

    op.drop_index(op.f('ix_captures_tableau_session_panneau_id'), table_name='captures_tableau_session')
    op.drop_index(op.f('ix_captures_tableau_session_session_id'), table_name='captures_tableau_session')
    op.drop_table('captures_tableau_session')

    op.drop_index(op.f('ix_demandes_craie_eleve_utilisateur_id'), table_name='demandes_craie')
    op.drop_index(op.f('ix_demandes_craie_session_id'), table_name='demandes_craie')
    op.drop_table('demandes_craie')
    sa.Enum(name='statutdemandecraie').drop(op.get_bind(), checkfirst=True)

    op.drop_index(
        op.f('ix_permissions_ecriture_tableau_eleve_utilisateur_id'), table_name='permissions_ecriture_tableau'
    )
    op.drop_index(op.f('ix_permissions_ecriture_tableau_session_id'), table_name='permissions_ecriture_tableau')
    op.drop_table('permissions_ecriture_tableau')
    sa.Enum(name='modepermissionecriture').drop(op.get_bind(), checkfirst=True)

    op.drop_index(op.f('ix_traits_tableau_auteur_id'), table_name='traits_tableau')
    op.drop_index(op.f('ix_traits_tableau_panneau_id'), table_name='traits_tableau')
    op.drop_table('traits_tableau')
    sa.Enum(name='typetraittableau').drop(op.get_bind(), checkfirst=True)

    op.drop_index(op.f('ix_panneaux_tableau_session_id'), table_name='panneaux_tableau')
    op.drop_table('panneaux_tableau')
