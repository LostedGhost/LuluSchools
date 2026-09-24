"""identite initial (utilisateurs, tuteurs, otp_verifications)

Revision ID: 0001_identite_initial
Revises:
Create Date: 2026-09-24

"""
import sqlalchemy as sa
from alembic import op

revision = "0001_identite_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "utilisateurs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("prenom", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("telephone", sa.String(length=30), nullable=True),
        sa.Column("mot_de_passe_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "TUTEUR",
                "ELEVE",
                "ENSEIGNANT",
                "ADMIN_ETABLISSEMENT",
                "ADMIN_MINISTERIEL",
                name="roleutilisateur",
            ),
            nullable=False,
        ),
        sa.Column("email_verifie", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_utilisateurs_email", "utilisateurs", ["email"], unique=True)

    op.create_table(
        "tuteurs",
        sa.Column(
            "utilisateur_id",
            sa.String(length=36),
            sa.ForeignKey("utilisateurs.id"),
            primary_key=True,
        ),
        sa.Column("piece_identite_type", sa.String(length=50), nullable=True),
        sa.Column("piece_identite_numero", sa.String(length=100), nullable=True),
    )

    op.create_table(
        "otp_verifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False
        ),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("salt", sa.String(length=32), nullable=False),
        sa.Column("tentatives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("utilisee", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_otp_verifications_utilisateur_id", "otp_verifications", ["utilisateur_id"])


def downgrade() -> None:
    op.drop_index("ix_otp_verifications_utilisateur_id", table_name="otp_verifications")
    op.drop_table("otp_verifications")
    op.drop_table("tuteurs")
    op.drop_index("ix_utilisateurs_email", table_name="utilisateurs")
    op.drop_table("utilisateurs")
