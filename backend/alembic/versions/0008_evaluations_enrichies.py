"""evaluations enrichies - nature formative/sommative, sujet/bareme document, copie image

Revision ID: 0008_evaluations_enrichies
Revises: 0007_vie_scolaire
Create Date: 2026-09-26

UC-26 : nature (formative exclue du calcul du bulletin), sujet libre en document
(image/PDF) en plus du formulaire de questions, bareme GLOBAL en document (jamais
expose a l'eleve, comme bareme_reponse), et soumission alternative entierement imagee
(copie scannee/photographiee, corrigee de facon holistique - voir
FreeLLMClient.corriger_copie_image).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0008_evaluations_enrichies'
down_revision = '0007_vie_scolaire'
branch_labels = None
depends_on = None

# Contrairement a un Enum cree au sein d'un create_table (qui emet lui-meme le CREATE
# TYPE Postgres), un add_column sur une table EXISTANTE ne le fait pas automatiquement -
# creation explicite requise ici (premier cas du projet a ajouter une colonne Enum apres
# coup plutot qu'a la creation de sa table).
_type_nature_evaluation = postgresql.ENUM('FORMATIVE', 'SOMMATIVE', name='natureevaluation')


def upgrade() -> None:
    _type_nature_evaluation.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'devoirs',
        sa.Column('nature', _type_nature_evaluation, nullable=False, server_default='SOMMATIVE'),
    )
    op.add_column('devoirs', sa.Column('sujet_lulufiles_file_id', sa.String(length=36), nullable=True))
    op.add_column('devoirs', sa.Column('bareme_document_lulufiles_file_id', sa.String(length=36), nullable=True))
    op.add_column('soumissions', sa.Column('copie_image_lulufiles_file_id', sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column('soumissions', 'copie_image_lulufiles_file_id')
    op.drop_column('devoirs', 'bareme_document_lulufiles_file_id')
    op.drop_column('devoirs', 'sujet_lulufiles_file_id')
    op.drop_column('devoirs', 'nature')
    _type_nature_evaluation.drop(op.get_bind(), checkfirst=True)
