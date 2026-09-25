"""lignes_transport, tickets_transport, types_repas_cantine, tickets_cantine (UC-11/UC-12)

Revision ID: 0014_services_scolaires
Revises: 0013_designations_controleur
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_services_scolaires"
down_revision = "0013_designations_controleur"
branch_labels = None
depends_on = None

# create_type=False : le type est partage par les deux tables (tickets_transport et
# tickets_cantine) dans cette meme migration ; sans ce flag, op.create_table tenterait
# de le re-creer pour la seconde table et echouerait ("type already exists"). Cree une
# seule fois explicitement ci-dessous via .create(checkfirst=True).
_statut_ticket = postgresql.ENUM(
    "ACHETE", "VALIDE", "EXPIRE", "REMBOURSE", name="statutticket", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    _statut_ticket.create(bind, checkfirst=True)

    op.create_table(
        "lignes_transport",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("prix", sa.Float(), nullable=False),
        sa.Column("capacite_par_trajet", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lignes_transport_etablissement_id", "lignes_transport", ["etablissement_id"])

    op.create_table(
        "tickets_transport",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ligne_id", sa.String(length=36), sa.ForeignKey("lignes_transport.id"), nullable=False),
        sa.Column("utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column("date_trajet", sa.Date(), nullable=False),
        sa.Column("statut", _statut_ticket, nullable=False),
        sa.Column("prix_paye", sa.Float(), nullable=False),
        sa.Column("paiement_confirme", sa.Boolean(), nullable=False),
        sa.Column("kkiapay_transaction_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tickets_transport_ligne_id", "tickets_transport", ["ligne_id"])
    op.create_index("ix_tickets_transport_utilisateur_id", "tickets_transport", ["utilisateur_id"])
    op.create_index(
        "ix_tickets_transport_kkiapay_transaction_id",
        "tickets_transport",
        ["kkiapay_transaction_id"],
        unique=True,
    )

    op.create_table(
        "types_repas_cantine",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("prix", sa.Float(), nullable=False),
        sa.Column("capacite_par_jour", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_types_repas_cantine_etablissement_id", "types_repas_cantine", ["etablissement_id"])

    op.create_table(
        "tickets_cantine",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "type_repas_id", sa.String(length=36), sa.ForeignKey("types_repas_cantine.id"), nullable=False
        ),
        sa.Column("utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column("date_service", sa.Date(), nullable=False),
        sa.Column("statut", _statut_ticket, nullable=False),
        sa.Column("prix_paye", sa.Float(), nullable=False),
        sa.Column("paiement_confirme", sa.Boolean(), nullable=False),
        sa.Column("kkiapay_transaction_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tickets_cantine_type_repas_id", "tickets_cantine", ["type_repas_id"])
    op.create_index("ix_tickets_cantine_utilisateur_id", "tickets_cantine", ["utilisateur_id"])
    op.create_index(
        "ix_tickets_cantine_kkiapay_transaction_id",
        "tickets_cantine",
        ["kkiapay_transaction_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_tickets_cantine_kkiapay_transaction_id", table_name="tickets_cantine")
    op.drop_index("ix_tickets_cantine_utilisateur_id", table_name="tickets_cantine")
    op.drop_index("ix_tickets_cantine_type_repas_id", table_name="tickets_cantine")
    op.drop_table("tickets_cantine")

    op.drop_index("ix_types_repas_cantine_etablissement_id", table_name="types_repas_cantine")
    op.drop_table("types_repas_cantine")

    op.drop_index("ix_tickets_transport_kkiapay_transaction_id", table_name="tickets_transport")
    op.drop_index("ix_tickets_transport_utilisateur_id", table_name="tickets_transport")
    op.drop_index("ix_tickets_transport_ligne_id", table_name="tickets_transport")
    op.drop_table("tickets_transport")

    op.drop_index("ix_lignes_transport_etablissement_id", table_name="lignes_transport")
    op.drop_table("lignes_transport")

    _statut_ticket.drop(op.get_bind(), checkfirst=True)
