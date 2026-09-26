"""etablissements_geolocalisation - latitude/longitude par etablissement

Revision ID: 0003_etablissements_geolocalisation
Revises: 0002_micro_jobs_offre_client
Create Date: 2026-09-26

Ajoute latitude/longitude a Etablissement pour la nouvelle section "Cartes" (liens
Google Maps) et l'affichage de la position sur les pages de presentation publiques.
Colonnes nullables en base (les lignes existantes n'ont pas encore de coordonnees et
aucune migration de donnees reelles n'est necessaire a ce stade), mais desormais
obligatoires cote application pour toute NOUVELLE creation (EtablissementCreate) -
objectif produit : une geolocalisation pour tous les etablissements a terme.
"""
from alembic import op
import sqlalchemy as sa


revision = '0003_etablissements_geolocalisation'
down_revision = '0002_micro_jobs_offre_client'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('etablissements', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('etablissements', sa.Column('longitude', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('etablissements', 'longitude')
    op.drop_column('etablissements', 'latitude')
