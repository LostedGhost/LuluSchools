"""Lot 7.8 : EFTP (type d'enseignement), offres et candidatures de stage, competences
metier, critere automatique des bourses scientifiques

Revision ID: 0026_eftp_stages_bourses
Revises: 0025_alphabetisation
Create Date: 2026-09-29 04:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

_STATUT = postgresql.ENUM('ENVOYEE', 'RETENUE', 'NON_RETENUE', name='statutcandidaturestage', create_type=False)
_NIVEAU = postgresql.ENUM('INITIE', 'CONFIRME', 'MAITRISE', name='niveaucompetence', create_type=False)


revision = '0026_eftp_stages_bourses'
down_revision = '0025_alphabetisation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE classes ADD COLUMN IF NOT EXISTS enseignement VARCHAR(20)")
    op.execute("ALTER TABLE types_acte_academique ADD COLUMN IF NOT EXISTS critere_automatique VARCHAR(40)")
    _STATUT.create(op.get_bind(), checkfirst=True)
    _NIVEAU.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'offres_stage',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('etablissement_id', sa.String(length=36), nullable=False),
        sa.Column('entreprise', sa.String(length=200), nullable=False),
        sa.Column('intitule', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('lieu', sa.String(length=120), nullable=False),
        sa.Column('filiere', sa.String(length=100), nullable=True),
        sa.Column('duree_semaines', sa.Integer(), nullable=False),
        sa.Column('date_limite', sa.Date(), nullable=False),
        sa.Column('contact', sa.String(length=200), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('publie_par_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['etablissement_id'], ['etablissements.id']),
        sa.ForeignKeyConstraint(['publie_par_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_index('ix_offres_stage_etablissement_id', 'offres_stage', ['etablissement_id'], if_not_exists=True)
    op.create_table(
        'candidatures_stage',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('offre_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('statut', _STATUT, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['offre_id'], ['offres_stage.id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('offre_id', 'eleve_utilisateur_id', name='uq_candidature_stage'),
        if_not_exists=True,
    )
    op.create_index('ix_candidatures_stage_offre_id', 'candidatures_stage', ['offre_id'], if_not_exists=True)
    op.create_index('ix_candidatures_stage_eleve_utilisateur_id', 'candidatures_stage', ['eleve_utilisateur_id'], if_not_exists=True)
    op.create_table(
        'competences_metier',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column('intitule', sa.String(length=200), nullable=False),
        sa.Column('niveau', _NIVEAU, nullable=False),
        sa.Column('valide_par_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.ForeignKeyConstraint(['valide_par_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_index('ix_competences_metier_eleve_utilisateur_id', 'competences_metier', ['eleve_utilisateur_id'], if_not_exists=True)


def downgrade() -> None:
    op.drop_table('competences_metier')
    op.drop_table('candidatures_stage')
    op.drop_table('offres_stage')
    sa.Enum(name='niveaucompetence').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='statutcandidaturestage').drop(op.get_bind(), checkfirst=True)
    op.drop_column('types_acte_academique', 'critere_automatique')
    op.drop_column('classes', 'enseignement')
