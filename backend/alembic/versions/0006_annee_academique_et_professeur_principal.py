"""annee_academique sur classes + professeur principal sur affectation

Revision ID: 0006_annee_academique
Revises: 0005_affectation_enseignant
Create Date: 2026-09-26

UC-24 : une Classe devient une instance annuelle precise (une '6eme A' en 2025-2026
n'est pas la meme instance qu'en 2026-2027) - affectations et inscriptions restent
scopees par annee sans changer leur propre schema, puisqu'elles pointent deja vers une
Classe precise via classe_id. Les lignes existantes sont retro-datees a l'annee
academique en cours au moment de cette migration (aucune donnee de production reelle
attendue avant ce commit).

UC-23 : au plus un professeur principal par classe (voir vie_scolaire) - simple
booleen sur AffectationEnseignant, invariant "un seul par classe" applique cote
applicatif (voir POST /classes/{id}/professeur-principal), pas par contrainte SQL.

**Fusion du 2026-09-26** : cette migration ajoutait aussi `classes.annee_academique`,
en parallele et sans le savoir de `0007_admin_etab` (branche soeur depuis
`0005_affectation_enseignant`, developpee simultanement pour le lot admin
etablissement) qui ajoute la MEME colonne. Sur un historique lineaire, les deux
branches finissent toutes les deux appliquees avant la migration de fusion
(`0015_fusion_lots`) sans ordre garanti entre elles - un second `ADD COLUMN` sur la
meme colonne echoue toujours (`DuplicateColumn`), quel que soit l'ordre. Retire ici :
`0007_admin_etab` en reste desormais l'unique proprietaire (colonne + index), cette
migration ne touche plus que `affectations_enseignant.est_professeur_principal`.
"""
from alembic import op
import sqlalchemy as sa


revision = '0006_annee_academique'
down_revision = '0005_affectation_enseignant'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'affectations_enseignant',
        sa.Column('est_professeur_principal', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('affectations_enseignant', 'est_professeur_principal')
