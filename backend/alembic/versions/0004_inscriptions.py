"""eleves, inscriptions

Revision ID: 0004_inscriptions
Revises: 0003_etablissements_classes
Create Date: 2026-09-24

"""
import sqlalchemy as sa
from alembic import op

revision = "0004_inscriptions"
down_revision = "0003_etablissements_classes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eleves",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("prenom", sa.String(length=100), nullable=False),
        sa.Column("date_naissance", sa.Date(), nullable=False),
        sa.Column("matricule", sa.String(length=30), nullable=True),
        sa.Column("tuteur_id", sa.String(length=36), sa.ForeignKey("tuteurs.utilisateur_id"), nullable=True),
        sa.Column(
            "utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_eleves_matricule", "eleves", ["matricule"], unique=True)
    op.create_unique_constraint("uq_eleves_utilisateur_id", "eleves", ["utilisateur_id"])

    op.create_table(
        "inscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("eleve_id", sa.String(length=36), sa.ForeignKey("eleves.id"), nullable=False),
        sa.Column("classe_id", sa.String(length=36), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column(
            "statut",
            sa.Enum(
                "EN_ATTENTE_CONSENTEMENT_PARENTAL",
                "SOUMISE",
                "VALIDEE",
                "REJETEE",
                name="statutinscription",
            ),
            nullable=False,
        ),
        sa.Column("consentement_parental_horodatage", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motif_rejet", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inscriptions_eleve_id", "inscriptions", ["eleve_id"])
    op.create_index("ix_inscriptions_classe_id", "inscriptions", ["classe_id"])


def downgrade() -> None:
    op.drop_index("ix_inscriptions_classe_id", table_name="inscriptions")
    op.drop_index("ix_inscriptions_eleve_id", table_name="inscriptions")
    op.drop_table("inscriptions")

    op.drop_constraint("uq_eleves_utilisateur_id", "eleves", type_="unique")
    op.drop_index("ix_eleves_matricule", table_name="eleves")
    op.drop_table("eleves")
