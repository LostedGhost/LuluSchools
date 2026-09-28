"""Saisie papier : registre des documents papier lus par l'IA et valides par l'administration

Revision ID: 0020_saisie_papier
Revises: 0019_simplification_admin
Create Date: 2026-09-28 20:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Types crees a part (checkfirst) : migration rejouable sur une base deja construite par
# create_all puis estampillee (cf. 0017).
_TYPE = postgresql.ENUM('FEUILLE_NOTES', 'FEUILLE_APPEL', 'COURS', 'FICHE_INSCRIPTION', 'COPIE', 'CONTRAT_SIGNE',
                        'CONSENTEMENT', name='typedocumentpapier', create_type=False)
_STATUT = postgresql.ENUM('LU', 'ENREGISTRE', name='statutdocumentpapier', create_type=False)


revision = '0020_saisie_papier'
down_revision = '0019_simplification_admin'
branch_labels = None
depends_on = None


def upgrade() -> None:
    _TYPE.create(op.get_bind(), checkfirst=True)
    _STATUT.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'documents_papier',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('etablissement_id', sa.String(length=36), nullable=False),
        sa.Column('type', _TYPE, nullable=False),
        sa.Column('statut', _STATUT, nullable=False),
        sa.Column('fichiers', sa.JSON(), nullable=False),
        sa.Column('lecture_ia', sa.JSON(), nullable=True),
        sa.Column('donnees_enregistrees', sa.JSON(), nullable=True),
        sa.Column('objet_type', sa.String(length=40), nullable=True),
        sa.Column('objet_id', sa.String(length=36), nullable=True),
        sa.Column('saisi_par_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('enregistre_le', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['etablissement_id'], ['etablissements.id']),
        sa.ForeignKeyConstraint(['saisi_par_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_index('ix_documents_papier_etablissement_id', 'documents_papier', ['etablissement_id'], if_not_exists=True)
    op.create_index('ix_documents_papier_objet_id', 'documents_papier', ['objet_id'], if_not_exists=True)
    op.create_index('ix_documents_papier_saisi_par_id', 'documents_papier', ['saisi_par_id'], if_not_exists=True)


def downgrade() -> None:
    op.drop_table('documents_papier')
    sa.Enum(name='typedocumentpapier').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='statutdocumentpapier').drop(op.get_bind(), checkfirst=True)
