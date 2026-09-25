"""soumissions : ajoute le statut en_correction (correction IA passee en arriere-plan)

Revision ID: 0012_soumissions_en_correction
Revises: 0011_eleves_nationalite
Create Date: 2026-09-25

"""
from alembic import op

revision = "0012_soumissions_en_correction"
down_revision = "0011_eleves_nationalite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE ne peut pas etre execute dans le meme bloc transactionnel
    # que son utilisation, mais Alembic l'encapsule par defaut dans une transaction : on
    # sort explicitement de la transaction pour cette instruction (pattern standard
    # Postgres pour l'ajout d'une valeur d'enum).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE statutsoumission ADD VALUE IF NOT EXISTS 'EN_CORRECTION' BEFORE 'CORRIGEE'")


def downgrade() -> None:
    # Postgres ne supporte pas DROP VALUE sur un enum : un downgrade reel demanderait de
    # recreer le type (comme fait en 0010) ; pas necessaire tant qu'aucune donnee reelle
    # n'utilise cette valeur (voir note sur 0010 dans PROJECT_MAP.md).
    pass
