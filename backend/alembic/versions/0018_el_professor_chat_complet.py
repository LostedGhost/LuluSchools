"""El Professor : conversations completes (aide generale, pieces jointes, alertes eleve)

- sessions_el_professor : cours_id facultatif (conversation d'aide generale) et sujet.
- messages El Professor (4 personas) : nom, type et texte extrait de la piece jointe.
- cours.texte_extrait : texte d'un cours PDF, fourni a El Professor et aux quiz.
- origine d'alerte ELEVE : signal de danger dans une conversation d'eleve.

Revision ID: 0018_el_professor_chat
Revises: 0017_limitation_debit
Create Date: 2026-09-27 20:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0018_el_professor_chat'
down_revision = '0017_limitation_debit'
branch_labels = None
depends_on = None

_TABLES_MESSAGES = (
    'messages_el_professor',
    'messages_el_professor_enseignant',
    'messages_el_professor_tuteur',
    'messages_el_professor_famille',
)


def upgrade() -> None:
    if op.get_bind().dialect.name == 'postgresql':
        op.execute("ALTER TYPE originealerteelprofessor ADD VALUE IF NOT EXISTS 'ELEVE'")

    with op.batch_alter_table('sessions_el_professor') as batch:
        batch.alter_column('cours_id', existing_type=sa.String(length=36), nullable=True)
        batch.add_column(sa.Column('sujet', sa.String(length=200), nullable=True))

    for table in _TABLES_MESSAGES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column('piece_jointe_nom', sa.String(length=255), nullable=True))
            batch.add_column(sa.Column('piece_jointe_type', sa.String(length=100), nullable=True))
            batch.add_column(sa.Column('piece_jointe_texte', sa.Text(), nullable=True))

    with op.batch_alter_table('cours') as batch:
        batch.add_column(sa.Column('texte_extrait', sa.Text(), nullable=True))


def downgrade() -> None:
    # La valeur ELEVE du type enum reste en place (PostgreSQL ne sait pas retirer une valeur).
    with op.batch_alter_table('cours') as batch:
        batch.drop_column('texte_extrait')

    for table in _TABLES_MESSAGES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column('piece_jointe_texte')
            batch.drop_column('piece_jointe_type')
            batch.drop_column('piece_jointe_nom')

    op.execute("DELETE FROM messages_el_professor WHERE session_id IN "
               "(SELECT id FROM sessions_el_professor WHERE cours_id IS NULL)")
    op.execute("DELETE FROM sessions_el_professor WHERE cours_id IS NULL")
    with op.batch_alter_table('sessions_el_professor') as batch:
        batch.drop_column('sujet')
        batch.alter_column('cours_id', existing_type=sa.String(length=36), nullable=False)
