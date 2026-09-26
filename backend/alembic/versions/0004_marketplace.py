"""marketplace - annonces, photos, signalements, transactions et contestations (UC-20/21/22)

Revision ID: 0004_marketplace
Revises: 0003_etablissements_geolocalisation
Create Date: 2026-09-26

Phase 4 : marketplace etudiante entre eleves d'un meme etablissement, sequestre Kkiapay
"Option A" identique a UC-18 (ADR-008) - voir docs/contrat-api-phase-4-marketplace.md.
"""
from alembic import op
import sqlalchemy as sa


revision = '0004_marketplace'
down_revision = '0003_etablissements_geolocalisation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'annonces_marketplace',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('etablissement_id', sa.String(length=36), nullable=False),
        sa.Column('vendeur_id', sa.String(length=36), nullable=False),
        sa.Column('titre', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column(
            'categorie',
            sa.Enum(
                'FOURNITURES_SCOLAIRES', 'MANUELS_LIVRES', 'VETEMENTS_UNIFORMES', 'ELECTRONIQUE', 'AUTRE',
                name='categorieannonce',
            ),
            nullable=False,
        ),
        sa.Column('etat', sa.Enum('NEUF', 'TRES_BON_ETAT', 'BON_ETAT', 'USE', name='etatarticle'), nullable=False),
        sa.Column('prix', sa.Float(), nullable=False),
        sa.Column(
            'statut',
            sa.Enum('DISPONIBLE', 'RESERVEE', 'VENDUE', 'RETIREE', name='statutannonce'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['etablissement_id'], ['etablissements.id']),
        sa.ForeignKeyConstraint(['vendeur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_annonces_marketplace_etablissement_id'), 'annonces_marketplace', ['etablissement_id'])
    op.create_index(op.f('ix_annonces_marketplace_vendeur_id'), 'annonces_marketplace', ['vendeur_id'])

    op.create_table(
        'photos_annonce_marketplace',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('annonce_id', sa.String(length=36), nullable=False),
        sa.Column('lulufiles_file_id', sa.String(length=100), nullable=False),
        sa.Column('ordre', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['annonce_id'], ['annonces_marketplace.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_photos_annonce_marketplace_annonce_id'), 'photos_annonce_marketplace', ['annonce_id'])

    op.create_table(
        'signalements_annonce_marketplace',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('annonce_id', sa.String(length=36), nullable=False),
        sa.Column('signale_par_id', sa.String(length=36), nullable=False),
        sa.Column('traite', sa.Boolean(), nullable=False),
        sa.Column('decision', sa.Text(), nullable=True),
        sa.Column('traite_par_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['annonce_id'], ['annonces_marketplace.id']),
        sa.ForeignKeyConstraint(['signale_par_id'], ['utilisateurs.id']),
        sa.ForeignKeyConstraint(['traite_par_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_signalements_annonce_marketplace_annonce_id'), 'signalements_annonce_marketplace', ['annonce_id']
    )

    op.create_table(
        'transactions_marketplace',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('annonce_id', sa.String(length=36), nullable=False),
        sa.Column('acheteur_id', sa.String(length=36), nullable=False),
        sa.Column(
            'statut',
            sa.Enum(
                'EN_ATTENTE_PAIEMENT', 'PAIEMENT_CONFIRME', 'REMISE_DECLAREE', 'CONFIRMEE', 'CONTESTEE',
                'FINALISEE', 'REMBOURSEE', 'ANNULEE',
                name='statuttransactionmarketplace',
            ),
            nullable=False,
        ),
        sa.Column('prix_paye', sa.Float(), nullable=False),
        sa.Column('paiement_confirme', sa.Boolean(), nullable=False),
        sa.Column('kkiapay_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('date_remise_declaree', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_limite_confirmation', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reference_paiement_vendeur', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['annonce_id'], ['annonces_marketplace.id']),
        sa.ForeignKeyConstraint(['acheteur_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kkiapay_transaction_id'),
    )
    op.create_index(op.f('ix_transactions_marketplace_annonce_id'), 'transactions_marketplace', ['annonce_id'])
    op.create_index(op.f('ix_transactions_marketplace_acheteur_id'), 'transactions_marketplace', ['acheteur_id'])

    op.create_table(
        'contestations_marketplace',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('transaction_id', sa.String(length=36), nullable=False),
        sa.Column('motif', sa.Text(), nullable=False),
        sa.Column(
            'statut',
            sa.Enum('EN_ATTENTE', 'ACCEPTEE', 'REJETEE', name='statutcontestationmarketplace'),
            nullable=False,
        ),
        sa.Column('decision_motif', sa.Text(), nullable=True),
        sa.Column('decision_par_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions_marketplace.id']),
        sa.ForeignKeyConstraint(['decision_par_id'], ['utilisateurs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id'),
    )
    op.create_index(
        op.f('ix_contestations_marketplace_transaction_id'), 'contestations_marketplace', ['transaction_id']
    )


def downgrade() -> None:
    op.drop_table('contestations_marketplace')
    op.drop_table('transactions_marketplace')
    op.drop_table('signalements_annonce_marketplace')
    op.drop_table('photos_annonce_marketplace')
    op.drop_table('annonces_marketplace')
    op.execute('DROP TYPE IF EXISTS statutcontestationmarketplace')
    op.execute('DROP TYPE IF EXISTS statuttransactionmarketplace')
    op.execute('DROP TYPE IF EXISTS statutannonce')
    op.execute('DROP TYPE IF EXISTS etatarticle')
    op.execute('DROP TYPE IF EXISTS categorieannonce')
