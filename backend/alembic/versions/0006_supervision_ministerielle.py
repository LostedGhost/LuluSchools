"""supervision_ministerielle - lot admin ministeriel (etablissements, comptes, contenus, audit)

Revision ID: 0006_supervision_min
Revises: 0005_affectation_enseignant
Create Date: 2026-09-26

Regroupe les changements de schema du lot "refonte admin ministeriel" (voir
docs/cahier-des-charges-refonte-admin-ministeriel.md et
docs/diagrammes-uml-phase-5-admin-ministeriel.md) : description/suspension d'etablissement
(UC-23/26/40/42), suspension de compte utilisateur (UC-35/50), masquage non destructif de
contenu pedagogique (UC-37/53) et le nouveau journal d'audit ministeriel (UC-36/51/52).
Un seul module `audit`, mais les colonnes touchent 3 tables existantes - regroupees dans
une seule migration par cohesion de lot (meme convention que 0004_marketplace.py).
"""
from alembic import op
import sqlalchemy as sa


revision = '0006_supervision_min'
down_revision = '0005_affectation_enseignant'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('etablissements', sa.Column('description', sa.Text(), nullable=True))
    op.add_column(
        'etablissements',
        sa.Column('actif', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column('etablissements', 'actif', server_default=None)

    op.add_column(
        'utilisateurs',
        sa.Column('actif', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column('utilisateurs', 'actif', server_default=None)

    op.add_column('cours', sa.Column('masque_par_id', sa.String(length=36), nullable=True))
    op.add_column('cours', sa.Column('masque_le', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_cours_masque_par_id_utilisateurs', 'cours', 'utilisateurs', ['masque_par_id'], ['id']
    )

    op.add_column('devoirs', sa.Column('masque_par_id', sa.String(length=36), nullable=True))
    op.add_column('devoirs', sa.Column('masque_le', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_devoirs_masque_par_id_utilisateurs', 'devoirs', 'utilisateurs', ['masque_par_id'], ['id']
    )

    op.create_table(
        'journal_audit_ministeriel',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('acteur_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('cible_type', sa.String(length=50), nullable=False),
        sa.Column('cible_id', sa.String(length=36), nullable=False),
        sa.Column('motif', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['acteur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_journal_audit_ministeriel_acteur_id'), 'journal_audit_ministeriel', ['acteur_id']
    )
    op.create_index(
        op.f('ix_journal_audit_ministeriel_cible_type'), 'journal_audit_ministeriel', ['cible_type']
    )
    op.create_index(
        op.f('ix_journal_audit_ministeriel_cible_id'), 'journal_audit_ministeriel', ['cible_id']
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_journal_audit_ministeriel_cible_id'), table_name='journal_audit_ministeriel')
    op.drop_index(op.f('ix_journal_audit_ministeriel_cible_type'), table_name='journal_audit_ministeriel')
    op.drop_index(op.f('ix_journal_audit_ministeriel_acteur_id'), table_name='journal_audit_ministeriel')
    op.drop_table('journal_audit_ministeriel')

    op.drop_constraint('fk_devoirs_masque_par_id_utilisateurs', 'devoirs', type_='foreignkey')
    op.drop_column('devoirs', 'masque_le')
    op.drop_column('devoirs', 'masque_par_id')

    op.drop_constraint('fk_cours_masque_par_id_utilisateurs', 'cours', type_='foreignkey')
    op.drop_column('cours', 'masque_le')
    op.drop_column('cours', 'masque_par_id')

    op.drop_column('utilisateurs', 'actif')

    op.drop_column('etablissements', 'actif')
    op.drop_column('etablissements', 'description')
