"""offres_micro_job, missions_micro_job, contestations_micro_job (UC-18)

Revision ID: 0020_micro_jobs
Revises: 0019_visites_virtuelles
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0020_micro_jobs"
down_revision = "0019_visites_virtuelles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "offres_micro_job",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("prestataire_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column("titre", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prix", sa.Float(), nullable=False),
        sa.Column("statut", sa.Enum("OUVERTE", "FERMEE", name="statutoffremicrojob"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_offres_micro_job_prestataire_id", "offres_micro_job", ["prestataire_id"])

    op.create_table(
        "missions_micro_job",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("offre_id", sa.String(length=36), sa.ForeignKey("offres_micro_job.id"), nullable=False),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column(
            "statut",
            sa.Enum(
                "EN_COURS", "TERMINEE_DECLAREE", "VALIDEE", "CONTESTEE", "REMBOURSEE", "PAYEE",
                name="statutmissionmicrojob",
            ),
            nullable=False,
        ),
        sa.Column("prix_paye", sa.Float(), nullable=False),
        sa.Column("paiement_confirme", sa.Boolean(), nullable=False),
        sa.Column("kkiapay_transaction_id", sa.String(length=100), nullable=True),
        sa.Column("date_declaration_fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_limite_validation", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_paiement_prestataire", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_missions_micro_job_offre_id", "missions_micro_job", ["offre_id"], unique=True)
    op.create_index("ix_missions_micro_job_client_id", "missions_micro_job", ["client_id"])
    op.create_index(
        "ix_missions_micro_job_kkiapay_transaction_id", "missions_micro_job", ["kkiapay_transaction_id"], unique=True
    )

    op.create_table(
        "contestations_micro_job",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("mission_id", sa.String(length=36), sa.ForeignKey("missions_micro_job.id"), nullable=False),
        sa.Column("motif", sa.Text(), nullable=False),
        sa.Column(
            "statut",
            sa.Enum("EN_ATTENTE", "ACCEPTEE", "REJETEE", name="statutcontestationmicrojob"),
            nullable=False,
        ),
        sa.Column("decision_motif", sa.Text(), nullable=True),
        sa.Column("decision_par_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_contestations_micro_job_mission_id", "contestations_micro_job", ["mission_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_contestations_micro_job_mission_id", table_name="contestations_micro_job")
    op.drop_table("contestations_micro_job")

    op.drop_index("ix_missions_micro_job_kkiapay_transaction_id", table_name="missions_micro_job")
    op.drop_index("ix_missions_micro_job_client_id", table_name="missions_micro_job")
    op.drop_index("ix_missions_micro_job_offre_id", table_name="missions_micro_job")
    op.drop_table("missions_micro_job")

    op.drop_index("ix_offres_micro_job_prestataire_id", table_name="offres_micro_job")
    op.drop_table("offres_micro_job")
