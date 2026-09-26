"""el professor famille (fil partage tuteur + enfant)

Revision ID: 0014_el_professor_famille
Revises: 0013_resume_session_live
Create Date: 2026-09-26

UC-37 : un tuteur peut inviter son enfant a rejoindre un fil El Professor partage,
les deux posant des questions dans le meme fil. `origineelalerteelprofessor` gagne la
valeur FAMILLE : une alerte declenchee dans un fil familial escalade toujours
directement vers l'administration, jamais uniquement vers le tuteur (UC-37.2, qui peut
etre la source du danger) - voir pedagogie/router.py::lister_alertes_el_professor_de_mon_enfant.
"""
from alembic import op
import sqlalchemy as sa


revision = '0014_el_professor_famille'
down_revision = '0013_resume_session_live'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE origineelalerteelprofessor ADD VALUE IF NOT EXISTS 'FAMILLE'")

    op.create_table(
        'sessions_el_professor_famille',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tuteur_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column('sujet', sa.String(length=200), nullable=True),
        sa.Column('rejointe_le', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tuteur_id'], ['tuteurs.utilisateur_id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_sessions_el_professor_famille_tuteur_id'), 'sessions_el_professor_famille', ['tuteur_id']
    )
    op.create_index(
        op.f('ix_sessions_el_professor_famille_eleve_utilisateur_id'),
        'sessions_el_professor_famille', ['eleve_utilisateur_id'],
    )

    op.create_table(
        'messages_el_professor_famille',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.Enum('TUTEUR', 'ELEVE', 'ASSISTANT', name='rolemessageelprofessorfamille'), nullable=False),
        sa.Column('contenu', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_el_professor_famille.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_messages_el_professor_famille_session_id'), 'messages_el_professor_famille', ['session_id']
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_messages_el_professor_famille_session_id'), table_name='messages_el_professor_famille')
    op.drop_table('messages_el_professor_famille')
    sa.Enum(name='rolemessageelprofessorfamille').drop(op.get_bind(), checkfirst=True)

    op.drop_index(
        op.f('ix_sessions_el_professor_famille_eleve_utilisateur_id'), table_name='sessions_el_professor_famille'
    )
    op.drop_index(op.f('ix_sessions_el_professor_famille_tuteur_id'), table_name='sessions_el_professor_famille')
    op.drop_table('sessions_el_professor_famille')

    # Retirer une valeur d'enum Postgres exige de recreer le type - les alertes FAMILLE
    # deja enregistrees sont requalifiees TUTEUR (comportement le plus proche disponible
    # dans le schema pre-UC-37) plutot que supprimees.
    op.execute("UPDATE alertes_el_professor SET origine = 'TUTEUR' WHERE origine = 'FAMILLE'")
    op.execute("ALTER TABLE alertes_el_professor ALTER COLUMN origine DROP DEFAULT")
    op.execute("ALTER TYPE origineelalerteelprofessor RENAME TO origineelalerteelprofessor_old")
    op.execute("CREATE TYPE origineelalerteelprofessor AS ENUM ('ENSEIGNANT', 'TUTEUR')")
    op.execute(
        "ALTER TABLE alertes_el_professor ALTER COLUMN origine TYPE origineelalerteelprofessor "
        "USING origine::text::origineelalerteelprofessor"
    )
    op.execute("ALTER TABLE alertes_el_professor ALTER COLUMN origine SET DEFAULT 'ENSEIGNANT'")
    op.execute("DROP TYPE origineelalerteelprofessor_old")
