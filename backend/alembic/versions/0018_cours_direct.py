"""sessions_live, consentements_camera_live, participations_live (UC-16)

Revision ID: 0018_cours_direct
Revises: 0017_el_professor_et_video
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0018_cours_direct"
down_revision = "0017_el_professor_et_video"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions_live",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("classe_id", sa.String(length=36), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column(
            "enseignant_id", sa.String(length=36), sa.ForeignKey("enseignants.utilisateur_id"), nullable=False
        ),
        sa.Column("date_heure", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "statut",
            sa.Enum("PLANIFIEE", "EN_COURS", "TERMINEE", name="statutsessionlive"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_live_classe_id", "sessions_live", ["classe_id"])
    op.create_index("ix_sessions_live_enseignant_id", "sessions_live", ["enseignant_id"])

    op.create_table(
        "consentements_camera_live",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("eleve_utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column("tuteur_id", sa.String(length=36), sa.ForeignKey("tuteurs.utilisateur_id"), nullable=False),
        sa.Column("date_consentement", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_consentements_camera_live_eleve_utilisateur_id",
        "consentements_camera_live",
        ["eleve_utilisateur_id"],
        unique=True,
    )

    op.create_table(
        "participations_live",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("sessions_live.id"), nullable=False),
        sa.Column("eleve_utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column("camera_autorisee", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "eleve_utilisateur_id", name="uq_participation_live"),
    )
    op.create_index("ix_participations_live_session_id", "participations_live", ["session_id"])
    op.create_index("ix_participations_live_eleve_utilisateur_id", "participations_live", ["eleve_utilisateur_id"])


def downgrade() -> None:
    op.drop_index("ix_participations_live_eleve_utilisateur_id", table_name="participations_live")
    op.drop_index("ix_participations_live_session_id", table_name="participations_live")
    op.drop_table("participations_live")

    op.drop_index("ix_consentements_camera_live_eleve_utilisateur_id", table_name="consentements_camera_live")
    op.drop_table("consentements_camera_live")

    op.drop_index("ix_sessions_live_enseignant_id", table_name="sessions_live")
    op.drop_index("ix_sessions_live_classe_id", table_name="sessions_live")
    op.drop_table("sessions_live")
