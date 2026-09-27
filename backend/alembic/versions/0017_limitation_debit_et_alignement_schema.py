"""limitation de debit en base et alignement du schema sur les modeles

- tentatives_limitees : compteurs de la limitation de debit (valables multi-workers).
- Types enum renommes comme les modeles (origineelalerteelprofessor, faute de frappe ;
  nature_entree_vie_scolaire).
- Unicite exprimee par un index unique (comme les modeles) plutot que par une contrainte
  doublee d'un index simple, sur trois colonnes.

Revision ID: 0017_limitation_debit
Revises: 0016_durcissement_securite
Create Date: 2026-09-27 15:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0017_limitation_debit'
down_revision = '0016_durcissement_securite'
branch_labels = None
depends_on = None

_UNICITES = [
    ("resumes_session_live", "session_id"),
    ("plafonds_familiaux", "eleve_utilisateur_id"),
    ("contestations_marketplace", "transaction_id"),
]


def upgrade() -> None:
    op.create_table(
        'tentatives_limitees',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('cle', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_tentatives_limitees_cle', 'tentatives_limitees', ['cle'])
    op.create_index('ix_tentatives_limitees_created_at', 'tentatives_limitees', ['created_at'])

    op.execute("ALTER TYPE origineelalerteelprofessor RENAME TO originealerteelprofessor")
    op.execute("ALTER TYPE nature_entree_vie_scolaire RENAME TO natureentreeviescolaire")

    for table, colonne in _UNICITES:
        op.drop_constraint(f"{table}_{colonne}_key", table, type_="unique")
        op.drop_index(f"ix_{table}_{colonne}", table_name=table)
        op.create_index(f"ix_{table}_{colonne}", table, [colonne], unique=True)


def downgrade() -> None:
    for table, colonne in _UNICITES:
        op.drop_index(f"ix_{table}_{colonne}", table_name=table)
        op.create_index(f"ix_{table}_{colonne}", table, [colonne], unique=False)
        op.create_unique_constraint(f"{table}_{colonne}_key", table, [colonne])

    op.execute("ALTER TYPE natureentreeviescolaire RENAME TO nature_entree_vie_scolaire")
    op.execute("ALTER TYPE originealerteelprofessor RENAME TO origineelalerteelprofessor")

    op.drop_index('ix_tentatives_limitees_created_at', table_name='tentatives_limitees')
    op.drop_index('ix_tentatives_limitees_cle', table_name='tentatives_limitees')
    op.drop_table('tentatives_limitees')
