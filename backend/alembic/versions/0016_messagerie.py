"""conversations, participants_conversation, messages, signalements_message (UC-13)

Revision ID: 0016_messagerie
Revises: 0015_billetterie
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0016_messagerie"
down_revision = "0015_billetterie"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("type", sa.Enum("DM", "GROUPE_CLASSE", name="typeconversation"), nullable=False),
        sa.Column("classe_id", sa.String(length=36), sa.ForeignKey("classes.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_classe_id", "conversations", ["classe_id"], unique=True)

    op.create_table(
        "participants_conversation",
        sa.Column(
            "conversation_id", sa.String(length=36), sa.ForeignKey("conversations.id"), primary_key=True
        ),
        sa.Column("utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), primary_key=True),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_id", sa.String(length=36), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("auteur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column("contenu", sa.Text(), nullable=False),
        sa.Column("masque_par", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_auteur_id", "messages", ["auteur_id"])

    op.create_table(
        "signalements_message",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("message_id", sa.String(length=36), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("signale_par_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=False),
        sa.Column("traite", sa.Boolean(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("traite_par_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signalements_message_message_id", "signalements_message", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_signalements_message_message_id", table_name="signalements_message")
    op.drop_table("signalements_message")

    op.drop_index("ix_messages_auteur_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")

    op.drop_table("participants_conversation")

    op.drop_index("ix_conversations_classe_id", table_name="conversations")
    op.drop_table("conversations")
