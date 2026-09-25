"""eleves : nationalite (necessaire au nouveau format de matricule)

Revision ID: 0011_eleves_nationalite
Revises: 0010_formulaires_llm
Create Date: 2026-09-25

"""
import sqlalchemy as sa
from alembic import op

revision = "0011_eleves_nationalite"
down_revision = "0010_formulaires_llm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    nationalite_enum = sa.Enum("NATIONALE", "ETRANGERE", name="nationalite")
    nationalite_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "eleves",
        sa.Column(
            "nationalite",
            nationalite_enum,
            nullable=False,
            server_default="NATIONALE",
        ),
    )
    op.alter_column("eleves", "nationalite", server_default=None)


def downgrade() -> None:
    op.drop_column("eleves", "nationalite")
    sa.Enum(name="nationalite").drop(op.get_bind(), checkfirst=True)
