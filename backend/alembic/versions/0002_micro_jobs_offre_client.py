"""micro_jobs_offre_client - la publication d'une offre devient payante et ouverte a tous

Revision ID: 0002_micro_jobs_offre_client
Revises: 0001_schema_initial
Create Date: 2026-09-26

Bascule UC-18 vers un modele "demande payee d'avance" : n'importe quel role
authentifie (Eleve inclus) peut publier une offre en tant que CLIENT, a condition de
payer le montant a la publication - le role de PRESTATAIRE (celui qui accepte et est
remunere) reste reserve aux roles majeurs (voir ADR-008 addendum, app/modules/
micro_jobs/models.py). Renomme les colonnes qui portaient l'ancien sens (le "prestataire"
publiait gratuitement, le "client" payait a l'acceptation) plutot que d'en ajouter de
nouvelles, pour ne pas laisser deux colonnes concurrentes portant la meme information.
"""
from alembic import op
import sqlalchemy as sa


revision = '0002_micro_jobs_offre_client'
down_revision = '0001_schema_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Bug reel trouve en appliquant cette migration pour la premiere fois contre un vrai
    # Postgres (2026-09-26, lot admin ministeriel) : alembic_version.version_num est un
    # VARCHAR(32) par defaut, mais nos identifiants de revision descriptifs depassent 32
    # caracteres a partir de la revision suivante ('0003_etablissements_geolocalisation',
    # 36 caracteres) - `alembic upgrade head` echouait donc silencieusement au moment de
    # passer de 0002 a 0003 (jamais exerce avant : aucune des migrations 0002-0005 n'avait
    # ete appliquee contre un Postgres reel jusqu'ici). Elargi ici (plutot que dans 0001,
    # deja applique en production - voir PROJECT_MAP) pour que ce soit fait avant le
    # premier identifiant de revision trop long.
    op.alter_column('alembic_version', 'version_num', type_=sa.String(length=255))

    # offres_micro_job.prestataire_id (l'ancien "qui offre le service") devient
    # client_id (celui qui publie ET paie) - la contrainte de cle etrangere suit
    # automatiquement le renommage de colonne sous Postgres.
    op.drop_index(op.f('ix_offres_micro_job_prestataire_id'), table_name='offres_micro_job')
    op.alter_column('offres_micro_job', 'prestataire_id', new_column_name='client_id')
    op.create_index(op.f('ix_offres_micro_job_client_id'), 'offres_micro_job', ['client_id'], unique=False)

    op.add_column(
        'offres_micro_job',
        sa.Column('paiement_confirme', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('offres_micro_job', 'paiement_confirme', server_default=None)
    op.add_column(
        'offres_micro_job', sa.Column('kkiapay_transaction_id', sa.String(length=100), nullable=True)
    )
    op.create_unique_constraint(
        'uq_offres_micro_job_kkiapay_transaction_id', 'offres_micro_job', ['kkiapay_transaction_id']
    )

    op.execute("ALTER TYPE statutoffremicrojob ADD VALUE IF NOT EXISTS 'EN_ATTENTE_PAIEMENT'")
    op.execute("ALTER TYPE statutoffremicrojob ADD VALUE IF NOT EXISTS 'ANNULEE'")

    # missions_micro_job.client_id (l'ancien "qui accepte et paie") devient
    # prestataire_id (celui qui accepte et est remunere pour le travail) - le paiement
    # est desormais deja confirme des la publication de l'offre, donc au moment ou une
    # mission est creee.
    op.drop_index(op.f('ix_missions_micro_job_client_id'), table_name='missions_micro_job')
    op.alter_column('missions_micro_job', 'client_id', new_column_name='prestataire_id')
    op.create_index(
        op.f('ix_missions_micro_job_prestataire_id'), 'missions_micro_job', ['prestataire_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_missions_micro_job_prestataire_id'), table_name='missions_micro_job')
    op.alter_column('missions_micro_job', 'prestataire_id', new_column_name='client_id')
    op.create_index(op.f('ix_missions_micro_job_client_id'), 'missions_micro_job', ['client_id'], unique=False)

    op.drop_constraint('uq_offres_micro_job_kkiapay_transaction_id', 'offres_micro_job', type_='unique')
    op.drop_column('offres_micro_job', 'kkiapay_transaction_id')
    op.drop_column('offres_micro_job', 'paiement_confirme')

    op.drop_index(op.f('ix_offres_micro_job_client_id'), table_name='offres_micro_job')
    op.alter_column('offres_micro_job', 'client_id', new_column_name='prestataire_id')
    op.create_index(op.f('ix_offres_micro_job_prestataire_id'), 'offres_micro_job', ['prestataire_id'], unique=False)

    # Note : Postgres ne permet pas de retirer des valeurs d'un type ENUM existant
    # (EN_ATTENTE_PAIEMENT / ANNULEE restent definies mais inutilisees apres ce downgrade).
