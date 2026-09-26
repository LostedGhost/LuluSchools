"""el professor - volet tuteur + alertes multi-origine

Revision ID: 0011_el_professor_tuteur
Revises: 0010_tableau_collaboratif
Create Date: 2026-09-26

UC-32 : conseil educatif/moral/professionnel pour le tuteur (a propos de son enfant),
avec le meme garde-fou de securite que le volet enseignant (UC-27.3). Les alertes
peuvent desormais venir d'une session ENSEIGNANT ou TUTEUR (deux tables distinctes) :
`alertes_el_professor.session_id` cesse d'etre une vraie ForeignKey (comme
DesignationControleur.evenement_id) et gagne `origine` + `eleve_utilisateur_id`
(denormalise, pour une requete directe "les alertes de mon enfant" cote tuteur).
"""
from alembic import op
import sqlalchemy as sa


revision = '0011_el_professor_tuteur'
down_revision = '0010_tableau_collaboratif'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sessions_el_professor_tuteur',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tuteur_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column('sujet', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tuteur_id'], ['tuteurs.utilisateur_id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_sessions_el_professor_tuteur_tuteur_id'), 'sessions_el_professor_tuteur', ['tuteur_id']
    )
    op.create_index(
        op.f('ix_sessions_el_professor_tuteur_eleve_utilisateur_id'),
        'sessions_el_professor_tuteur', ['eleve_utilisateur_id'],
    )

    op.create_table(
        'messages_el_professor_tuteur',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.Enum('TUTEUR', 'ASSISTANT', name='rolemessageelprofessortuteur'), nullable=False),
        sa.Column('contenu', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions_el_professor_tuteur.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_messages_el_professor_tuteur_session_id'), 'messages_el_professor_tuteur', ['session_id']
    )

    # alertes_el_professor : session_id cesse d'etre une vraie FK (peut desormais
    # referencer sessions_el_professor_enseignant OU sessions_el_professor_tuteur).
    op.drop_constraint('alertes_el_professor_session_id_fkey', 'alertes_el_professor', type_='foreignkey')

    origine_enum = sa.Enum('ENSEIGNANT', 'TUTEUR', name='origineelalerteelprofessor')
    origine_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'alertes_el_professor',
        sa.Column('origine', origine_enum, nullable=False, server_default='ENSEIGNANT'),
    )
    op.add_column('alertes_el_professor', sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'alertes_el_professor_eleve_utilisateur_id_fkey',
        'alertes_el_professor', 'utilisateurs', ['eleve_utilisateur_id'], ['id'],
    )
    op.create_index(
        op.f('ix_alertes_el_professor_eleve_utilisateur_id'), 'alertes_el_professor', ['eleve_utilisateur_id']
    )
    # Backfill des alertes deja existantes (toutes ENSEIGNANT a ce stade) avec l'eleve de
    # leur session - best effort, ne bloque jamais l'upgrade si la table est vide.
    op.execute(
        """
        UPDATE alertes_el_professor
        SET eleve_utilisateur_id = s.eleve_utilisateur_id
        FROM sessions_el_professor_enseignant s
        WHERE alertes_el_professor.session_id = s.id
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_alertes_el_professor_eleve_utilisateur_id'), table_name='alertes_el_professor')
    op.drop_constraint('alertes_el_professor_eleve_utilisateur_id_fkey', 'alertes_el_professor', type_='foreignkey')
    op.drop_column('alertes_el_professor', 'eleve_utilisateur_id')
    op.drop_column('alertes_el_professor', 'origine')
    sa.Enum(name='origineelalerteelprofessor').drop(op.get_bind(), checkfirst=True)
    op.create_foreign_key(
        'alertes_el_professor_session_id_fkey',
        'alertes_el_professor', 'sessions_el_professor_enseignant', ['session_id'], ['id'],
    )

    op.drop_index(op.f('ix_messages_el_professor_tuteur_session_id'), table_name='messages_el_professor_tuteur')
    op.drop_table('messages_el_professor_tuteur')
    sa.Enum(name='rolemessageelprofessortuteur').drop(op.get_bind(), checkfirst=True)

    op.drop_index(
        op.f('ix_sessions_el_professor_tuteur_eleve_utilisateur_id'), table_name='sessions_el_professor_tuteur'
    )
    op.drop_index(op.f('ix_sessions_el_professor_tuteur_tuteur_id'), table_name='sessions_el_professor_tuteur')
    op.drop_table('sessions_el_professor_tuteur')
