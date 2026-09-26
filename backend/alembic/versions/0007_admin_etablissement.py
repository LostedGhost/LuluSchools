"""admin_etablissement - annee academique, rentree, photo, formulaires dynamiques

Revision ID: 0007_admin_etab
Revises: 0006_supervision_min
Create Date: 2026-09-26

Regroupe les changements de schema du lot "refonte admin etablissement" (voir
docs/cahier-des-charges-refonte-admin-etablissement.md et
docs/diagrammes-uml-phase-6-admin-etablissement.md) : annee academique + filiere +
reconduction sur Classe (UC-43/44/58/59), rentree scolaire (UC-39/55), photo eleve/etudiant
(UC-42/57), formulaire dynamique partage recrutement+actes (UC-47/50/62/64) et livraison de
document d'acte (UC-52/66). Un seul module par usage, mais regroupees dans une seule
migration par cohesion de lot (meme convention que 0004_marketplace.py/0006_supervision_min.py).

**Fusion du 2026-09-26** : `Classe.annee_academique` (index compris) est desormais
uniquement ajoutee ici - la branche soeur `0006_annee_academique_et_professeur_principal`
ajoutait independamment la meme colonne (`DuplicateColumn` a la fusion des deux
branches sur un historique lineaire) ; retire de l'autre migration, voir son docstring.
"""
from alembic import op
import sqlalchemy as sa


revision = '0007_admin_etab'
down_revision = '0006_supervision_min'
branch_labels = None
depends_on = None

# Backfill des lignes Classe existantes (seed_mega.py) : aucune notion d'annee academique
# n'existait avant ce lot, toutes les classes existantes sont donc rattachees a l'annee en
# cours au moment de la migration plutot que laissees NULL (colonne NOT NULL des la creation,
# UC-43/58 exige une annee academique sur toute classe).
ANNEE_ACADEMIQUE_BACKFILL = '2026-2027'


def upgrade() -> None:
    op.add_column('classes', sa.Column('filiere', sa.String(length=100), nullable=True))
    op.add_column(
        'classes', sa.Column('annee_academique', sa.String(length=20), nullable=False, server_default=ANNEE_ACADEMIQUE_BACKFILL)
    )
    op.alter_column('classes', 'annee_academique', server_default=None)
    op.create_index(op.f('ix_classes_annee_academique'), 'classes', ['annee_academique'])
    op.add_column('classes', sa.Column('reconduite_depuis_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_classes_reconduite_depuis_id_classes', 'classes', 'classes', ['reconduite_depuis_id'], ['id']
    )

    op.create_table(
        'rentrees_scolaires',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('etablissement_id', sa.String(length=36), nullable=False),
        sa.Column('annee_academique', sa.String(length=20), nullable=False),
        sa.Column('statut', sa.Enum('OUVERTE', 'FERMEE', name='statutrentree'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['etablissement_id'], ['etablissements.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rentrees_scolaires_etablissement_id'), 'rentrees_scolaires', ['etablissement_id'])

    op.add_column('eleves', sa.Column('photo_lulufiles_id', sa.String(length=100), nullable=True))

    op.add_column('postes', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('postes', sa.Column('matiere', sa.String(length=100), nullable=True))
    op.add_column('postes', sa.Column('remuneration_min', sa.Float(), nullable=True))
    op.add_column('postes', sa.Column('remuneration_max', sa.Float(), nullable=True))
    op.add_column('postes', sa.Column('schema_formulaire', sa.JSON(), nullable=True))
    op.add_column('candidatures', sa.Column('reponses_formulaire', sa.JSON(), nullable=True))

    op.add_column('types_acte_academique', sa.Column('schema_formulaire', sa.JSON(), nullable=True))
    op.add_column('demandes_acte_academique', sa.Column('reponses_formulaire', sa.JSON(), nullable=True))
    op.add_column(
        'demandes_acte_academique', sa.Column('document_final_lulufiles_id', sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('demandes_acte_academique', 'document_final_lulufiles_id')
    op.drop_column('demandes_acte_academique', 'reponses_formulaire')
    op.drop_column('types_acte_academique', 'schema_formulaire')

    op.drop_column('candidatures', 'reponses_formulaire')
    op.drop_column('postes', 'schema_formulaire')
    op.drop_column('postes', 'remuneration_max')
    op.drop_column('postes', 'remuneration_min')
    op.drop_column('postes', 'matiere')
    op.drop_column('postes', 'description')

    op.drop_column('eleves', 'photo_lulufiles_id')

    op.drop_index(op.f('ix_rentrees_scolaires_etablissement_id'), table_name='rentrees_scolaires')
    op.drop_table('rentrees_scolaires')
    sa.Enum(name='statutrentree').drop(op.get_bind(), checkfirst=True)

    op.drop_constraint('fk_classes_reconduite_depuis_id_classes', 'classes', type_='foreignkey')
    op.drop_column('classes', 'reconduite_depuis_id')
    op.drop_index(op.f('ix_classes_annee_academique'), table_name='classes')
    op.drop_column('classes', 'annee_academique')
    op.drop_column('classes', 'filiere')
