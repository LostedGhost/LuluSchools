"""sessions_el_professor, messages_el_professor (UC-14) + format video sur cours (UC-15)

Revision ID: 0017_el_professor_et_video
Revises: 0016_messagerie
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0017_el_professor_et_video"
down_revision = "0016_messagerie"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE hors du bloc transactionnel d'Alembic (meme pattern que 0012).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE formatcours ADD VALUE IF NOT EXISTS 'VIDEO'")

    op.create_table(
        "sessions_el_professor",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("eleve_utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column("cours_id", sa.String(length=36), sa.ForeignKey("cours.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("eleve_utilisateur_id", "cours_id", name="uq_session_el_professor"),
    )
    op.create_index(
        "ix_sessions_el_professor_eleve_utilisateur_id", "sessions_el_professor", ["eleve_utilisateur_id"]
    )
    op.create_index("ix_sessions_el_professor_cours_id", "sessions_el_professor", ["cours_id"])

    op.create_table(
        "messages_el_professor",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id", sa.String(length=36), sa.ForeignKey("sessions_el_professor.id"), nullable=False
        ),
        sa.Column("role", sa.Enum("ELEVE", "ASSISTANT", name="rolemessageelprofessor"), nullable=False),
        sa.Column("contenu", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_el_professor_session_id", "messages_el_professor", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_el_professor_session_id", table_name="messages_el_professor")
    op.drop_table("messages_el_professor")

    op.drop_index("ix_sessions_el_professor_cours_id", table_name="sessions_el_professor")
    op.drop_index("ix_sessions_el_professor_eleve_utilisateur_id", table_name="sessions_el_professor")
    op.drop_table("sessions_el_professor")

    # Pas de downgrade reel pour la valeur d'enum ajoutee (Postgres ne supporte pas
    # DROP VALUE) - meme limitation deja documentee sur 0012.
