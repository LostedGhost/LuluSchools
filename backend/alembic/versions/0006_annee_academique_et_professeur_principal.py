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
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = '0006_annee_academique'
down_revision = '0005_affectation_enseignant'
branch_labels = None
depends_on = None


def _annee_academique_courante() -> str:
    aujourdhui = datetime.now(timezone.utc).date()
    if aujourdhui.month >= 9:
        return f"{aujourdhui.year}-{aujourdhui.year + 1}"
    return f"{aujourdhui.year - 1}-{aujourdhui.year}"


def upgrade() -> None:
    op.add_column('classes', sa.Column('annee_academique', sa.String(length=9), nullable=True))
    op.execute(
        sa.text("UPDATE classes SET annee_academique = :annee WHERE annee_academique IS NULL").bindparams(
            annee=_annee_academique_courante()
        )
    )
    op.alter_column('classes', 'annee_academique', nullable=False)
    op.create_index(op.f('ix_classes_annee_academique'), 'classes', ['annee_academique'])

    op.add_column(
        'affectations_enseignant',
        sa.Column('est_professeur_principal', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('affectations_enseignant', 'est_professeur_principal')
    op.drop_index(op.f('ix_classes_annee_academique'), table_name='classes')
    op.drop_column('classes', 'annee_academique')
