"""designations_controleur (Phase 2/3 : UC-11/UC-12/UC-17)

Revision ID: 0013_designations_controleur
Revises: 0012_soumissions_en_correction
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0013_designations_controleur"
down_revision = "0012_soumissions_en_correction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "designations_controleur",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
        sa.Column("utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column(
            "service", sa.Enum("TRANSPORT", "CANTINE", "EVENEMENT", name="servicecontrole"), nullable=False
        ),
        sa.Column("evenement_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_designations_controleur_etablissement_id", "designations_controleur", ["etablissement_id"]
    )
    op.create_index(
        "ix_designations_controleur_utilisateur_id", "designations_controleur", ["utilisateur_id"]
    )
    op.create_index(
        "ix_designations_controleur_evenement_id", "designations_controleur", ["evenement_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_designations_controleur_evenement_id", table_name="designations_controleur")
    op.drop_index("ix_designations_controleur_utilisateur_id", table_name="designations_controleur")
    op.drop_index("ix_designations_controleur_etablissement_id", table_name="designations_controleur")
    op.drop_table("designations_controleur")
