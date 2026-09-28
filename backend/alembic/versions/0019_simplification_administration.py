"""Simplification de l'administration : automatisations et aides de l'IA

- etablissements.admission_automatique : admission automatique des inscriptions.
- types_acte_academique.modele_document / demandes_acte_academique.analyse_ia : actes
  generes et livres automatiquement, avis de l'IA sur les reclamations.
- documents_candidature.tentatives_notation : renotation IA automatique.
- signalements (messages, annonces) : triage IA (gravite, resume, decision suggeree).
- contestations (marketplace, micro-jobs) : avis de l'IA.
- remboursement_effectue (tickets, billets, transactions, missions) : remboursement
  Kkiapay automatique. Les remboursements anterieurs a cette migration sont consideres
  comme deja traites (ils l'etaient a la main) : ils n'encombrent pas la boite « A traiter ».

Revision ID: 0019_simplification_admin
Revises: 0018_el_professor_chat
Create Date: 2026-09-28 12:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0019_simplification_admin'
down_revision = '0018_el_professor_chat'
branch_labels = None
depends_on = None

_TRIAGE = ('signalements_message', 'signalements_annonce_marketplace')
_AVIS = ('contestations_marketplace', 'contestations_micro_job')
# table -> (valeur du statut "rembourse" dans son type enum)
_REMBOURSEMENTS = {
    'tickets_transport': 'REMBOURSE',
    'tickets_cantine': 'REMBOURSE',
    'billets_evenement': 'REMBOURSE',
    'transactions_marketplace': 'REMBOURSEE',
    'missions_micro_job': 'REMBOURSEE',
}


def upgrade() -> None:
    op.add_column('etablissements', sa.Column('admission_automatique', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('types_acte_academique', sa.Column('modele_document', sa.String(length=40), nullable=True))
    op.add_column('demandes_acte_academique', sa.Column('analyse_ia', sa.Text(), nullable=True))
    op.add_column('documents_candidature', sa.Column('tentatives_notation', sa.Integer(), nullable=False, server_default='0'))
    for table in _TRIAGE:
        op.add_column(table, sa.Column('ia_gravite', sa.String(length=10), nullable=True))
        op.add_column(table, sa.Column('ia_resume', sa.Text(), nullable=True))
        op.add_column(table, sa.Column('ia_decision', sa.String(length=10), nullable=True))
    for table in _AVIS:
        op.add_column(table, sa.Column('ia_decision', sa.String(length=10), nullable=True))
        op.add_column(table, sa.Column('ia_justification', sa.Text(), nullable=True))
    for table, statut in _REMBOURSEMENTS.items():
        op.add_column(table, sa.Column('remboursement_effectue', sa.Boolean(), nullable=False, server_default=sa.false()))
        op.execute(f"UPDATE {table} SET remboursement_effectue = true WHERE statut = '{statut}'")


def downgrade() -> None:
    for table in _REMBOURSEMENTS:
        op.drop_column(table, 'remboursement_effectue')
    for table in _AVIS:
        op.drop_column(table, 'ia_justification')
        op.drop_column(table, 'ia_decision')
    for table in _TRIAGE:
        op.drop_column(table, 'ia_decision')
        op.drop_column(table, 'ia_resume')
        op.drop_column(table, 'ia_gravite')
    op.drop_column('documents_candidature', 'tentatives_notation')
    op.drop_column('demandes_acte_academique', 'analyse_ia')
    op.drop_column('types_acte_academique', 'modele_document')
    op.drop_column('etablissements', 'admission_automatique')
