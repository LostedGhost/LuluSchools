"""evenements, billets_evenement (UC-17)

Revision ID: 0015_billetterie
Revises: 0014_services_scolaires
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0015_billetterie"
down_revision = "0014_services_scolaires"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evenements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
        sa.Column("titre", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("lieu", sa.String(length=200), nullable=False),
        sa.Column("date_heure", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacite_max", sa.Integer(), nullable=False),
        sa.Column("prix_billet", sa.Float(), nullable=False),
        sa.Column("statut", sa.Enum("OUVERT", "ANNULE", name="statutevenement"), nullable=False),
        sa.Column("parrain_utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evenements_etablissement_id", "evenements", ["etablissement_id"])

    op.create_table(
        "billets_evenement",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("evenement_id", sa.String(length=36), sa.ForeignKey("evenements.id"), nullable=False),
        sa.Column("utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column(
            "statut",
            sa.Enum("ACHETE", "VALIDE", "EXPIRE", "REMBOURSE", name="statutbillet"),
            nullable=False,
        ),
        sa.Column("prix_paye", sa.Float(), nullable=False),
        sa.Column("paiement_confirme", sa.Boolean(), nullable=False),
        sa.Column("kkiapay_transaction_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_billets_evenement_evenement_id", "billets_evenement", ["evenement_id"])
    op.create_index("ix_billets_evenement_utilisateur_id", "billets_evenement", ["utilisateur_id"])
    op.create_index(
        "ix_billets_evenement_kkiapay_transaction_id", "billets_evenement", ["kkiapay_transaction_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_billets_evenement_kkiapay_transaction_id", table_name="billets_evenement")
    op.drop_index("ix_billets_evenement_utilisateur_id", table_name="billets_evenement")
    op.drop_index("ix_billets_evenement_evenement_id", table_name="billets_evenement")
    op.drop_table("billets_evenement")
    sa.Enum(name="statutbillet").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_evenements_etablissement_id", table_name="evenements")
    op.drop_table("evenements")
    sa.Enum(name="statutevenement").drop(op.get_bind(), checkfirst=True)
