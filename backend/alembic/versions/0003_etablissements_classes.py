"""etablissements, admins_etablissement, classes

Revision ID: 0003_etablissements_classes
Revises: 0002_identite_login_id
Create Date: 2026-09-24

"""
import sqlalchemy as sa
from alembic import op

revision = "0003_etablissements_classes"
down_revision = "0002_identite_login_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "etablissements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("type", sa.Enum("EP", "ES", "UP", name="typeetablissement"), nullable=False),
        sa.Column(
            "statut", sa.Enum("PUBLIC", "PRIVE", name="statutetablissement"), nullable=False
        ),
        sa.Column("code_etablissement", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_etablissements_code_etablissement",
        "etablissements",
        ["code_etablissement"],
        unique=True,
    )

    op.create_table(
        "admins_etablissement",
        sa.Column(
            "utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), primary_key=True
        ),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
    )
    op.create_index(
        "ix_admins_etablissement_etablissement_id",
        "admins_etablissement",
        ["etablissement_id"],
    )

    op.create_table(
        "classes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
        sa.Column("niveau", sa.String(length=100), nullable=False),
        sa.Column("capacite", sa.Integer(), nullable=False),
        sa.Column(
            "politique_depassement",
            sa.Enum(
                "ORDRE_ARRIVEE", "NOTES_CONCOURS", "TIRAGE_SORT", name="politiquedepassement"
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_classes_etablissement_id", "classes", ["etablissement_id"])


def downgrade() -> None:
    op.drop_index("ix_classes_etablissement_id", table_name="classes")
    op.drop_table("classes")

    op.drop_index("ix_admins_etablissement_etablissement_id", table_name="admins_etablissement")
    op.drop_table("admins_etablissement")

    op.drop_index("ix_etablissements_code_etablissement", table_name="etablissements")
    op.drop_table("etablissements")
