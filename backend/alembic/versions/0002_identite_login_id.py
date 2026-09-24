"""utilisateurs : login_id (email ou matricule), mot de passe temporaire, email optionnel

Revision ID: 0002_identite_login_id
Revises: 0001_identite_initial
Create Date: 2026-09-24

"""
import sqlalchemy as sa
from alembic import op

revision = "0002_identite_login_id"
down_revision = "0001_identite_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "utilisateurs",
        sa.Column("login_id", sa.String(length=255), nullable=False, server_default=""),
    )
    op.execute("UPDATE utilisateurs SET login_id = email WHERE login_id = ''")
    op.alter_column("utilisateurs", "login_id", server_default=None)
    op.create_index("ix_utilisateurs_login_id", "utilisateurs", ["login_id"], unique=True)

    op.add_column(
        "utilisateurs",
        sa.Column("mot_de_passe_temporaire", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("utilisateurs", "mot_de_passe_temporaire", server_default=None)

    # L'index unique existant (ix_utilisateurs_email) autorise deja plusieurs NULL en Postgres/SQLite,
    # il n'y a donc rien a recreer : juste assouplir la contrainte NOT NULL.
    op.alter_column("utilisateurs", "email", nullable=True)


def downgrade() -> None:
    op.alter_column("utilisateurs", "email", nullable=False)

    op.drop_column("utilisateurs", "mot_de_passe_temporaire")

    op.drop_index("ix_utilisateurs_login_id", table_name="utilisateurs")
    op.drop_column("utilisateurs", "login_id")
