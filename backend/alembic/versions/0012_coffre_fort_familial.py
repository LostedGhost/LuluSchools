"""coffre-fort familial

Revision ID: 0012_coffre_fort_familial
Revises: 0011_el_professor_tuteur
Create Date: 2026-09-26

UC-35 : supervision financiere opt-in du tuteur sur les depenses de son enfant
(micro-jobs client, marketplace, actes). `PlafondFamilial` porte la configuration
(un seul enregistrement par enfant, absence = aucune limite). `ValidationParentale`
s'intercale entre la creation d'une depense et l'amorcage de son paiement quand le
seuil de validation est depasse - `reference_id` n'est pas une vraie ForeignKey (comme
DesignationControleur.evenement_id), elle designe selon `module` une OffreMicroJob, une
TransactionMarketplace ou une DemandeActeAcademique. `AlerteDepassementPlafond` est une
notification passive (jamais bloquante) quand le plafond hebdomadaire est depasse.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0012_coffre_fort_familial'
down_revision = '0011_el_professor_tuteur'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'plafonds_familiaux',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tuteur_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column('plafond_hebdomadaire', sa.Float(), nullable=True),
        sa.Column('seuil_validation', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tuteur_id'], ['tuteurs.utilisateur_id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('eleve_utilisateur_id'),
    )
    op.create_index(op.f('ix_plafonds_familiaux_tuteur_id'), 'plafonds_familiaux', ['tuteur_id'])
    op.create_index(
        op.f('ix_plafonds_familiaux_eleve_utilisateur_id'), 'plafonds_familiaux', ['eleve_utilisateur_id']
    )

    # Le type Postgres est cree automatiquement par le premier create_table qui l'utilise
    # (checkfirst=False dans ce chemin d'alembic, voir le bug 0008 deja documente en sens
    # inverse pour add_column) - la deuxieme table qui reutilise ce meme nom d'enum doit
    # explicitement dire create_type=False, sinon la deuxieme create_table tente de
    # RE-creer le type et echoue avec DuplicateObject (invariant verifie manuellement
    # contre un vrai Postgres, pas seulement SQLite qui n'a pas de vrais types enum).
    op.create_table(
        'validations_parentales',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tuteur_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column('module', sa.Enum('MICRO_JOB', 'MARKETPLACE', 'ACTE', name='moduledepensecoffrefort'), nullable=False),
        sa.Column('reference_id', sa.String(length=36), nullable=False),
        sa.Column('montant', sa.Float(), nullable=False),
        sa.Column(
            'statut',
            sa.Enum('EN_ATTENTE', 'APPROUVEE', 'REFUSEE', name='statutvalidationparentale'),
            nullable=False,
        ),
        sa.Column('motif_refus', sa.Text(), nullable=True),
        sa.Column('decidee_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tuteur_id'], ['tuteurs.utilisateur_id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_validations_parentales_tuteur_id'), 'validations_parentales', ['tuteur_id'])
    op.create_index(
        op.f('ix_validations_parentales_eleve_utilisateur_id'), 'validations_parentales', ['eleve_utilisateur_id']
    )
    op.create_index(op.f('ix_validations_parentales_reference_id'), 'validations_parentales', ['reference_id'])

    op.create_table(
        'alertes_depassement_plafond',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tuteur_id', sa.String(length=36), nullable=False),
        sa.Column('eleve_utilisateur_id', sa.String(length=36), nullable=False),
        sa.Column(
            'module',
            postgresql.ENUM('MICRO_JOB', 'MARKETPLACE', 'ACTE', name='moduledepensecoffrefort', create_type=False),
            nullable=False,
        ),
        sa.Column('montant_semaine', sa.Float(), nullable=False),
        sa.Column('plafond', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tuteur_id'], ['tuteurs.utilisateur_id']),
        sa.ForeignKeyConstraint(['eleve_utilisateur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_alertes_depassement_plafond_tuteur_id'), 'alertes_depassement_plafond', ['tuteur_id']
    )
    op.create_index(
        op.f('ix_alertes_depassement_plafond_eleve_utilisateur_id'),
        'alertes_depassement_plafond', ['eleve_utilisateur_id'],
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_alertes_depassement_plafond_eleve_utilisateur_id'), table_name='alertes_depassement_plafond'
    )
    op.drop_index(op.f('ix_alertes_depassement_plafond_tuteur_id'), table_name='alertes_depassement_plafond')
    op.drop_table('alertes_depassement_plafond')

    op.drop_index(op.f('ix_validations_parentales_reference_id'), table_name='validations_parentales')
    op.drop_index(op.f('ix_validations_parentales_eleve_utilisateur_id'), table_name='validations_parentales')
    op.drop_index(op.f('ix_validations_parentales_tuteur_id'), table_name='validations_parentales')
    op.drop_table('validations_parentales')
    sa.Enum(name='statutvalidationparentale').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='moduledepensecoffrefort').drop(op.get_bind(), checkfirst=True)

    op.drop_index(op.f('ix_plafonds_familiaux_eleve_utilisateur_id'), table_name='plafonds_familiaux')
    op.drop_index(op.f('ix_plafonds_familiaux_tuteur_id'), table_name='plafonds_familiaux')
    op.drop_table('plafonds_familiaux')
