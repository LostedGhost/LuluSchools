"""casier_judiciaire_chiffre (stockage en base chiffre, plus de disque local)

Revision ID: 0022_casier_judiciaire_chiffre
Revises: 0021_etablissement_photos
Create Date: 2026-09-25

Le plan Render gratuit ne fournit pas de disque persistant (voir render.yaml / ADR-006) :
un fichier ecrit sur le disque local du service serait perdu au prochain redemarrage
(y compris la mise en veille apres 15 min d'inactivite). Le contenu du casier judiciaire
est donc desormais chiffre (Fernet, cle CASIER_JUDICIAIRE_ENCRYPTION_KEY hors depot) et
stocke directement dans la base Postgres, qui persiste independamment du service web.
"""
import sqlalchemy as sa
from alembic import op

revision = "0022_casier_judiciaire_chiffre"
down_revision = "0021_etablissement_photos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "verifications_casier_judiciaire",
        sa.Column("contenu_chiffre", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "verifications_casier_judiciaire",
        sa.Column("nom_fichier", sa.String(length=255), nullable=True),
    )
    op.drop_column("verifications_casier_judiciaire", "chemin_fichier_local")


def downgrade() -> None:
    op.add_column(
        "verifications_casier_judiciaire",
        sa.Column("chemin_fichier_local", sa.String(length=500), nullable=True),
    )
    op.drop_column("verifications_casier_judiciaire", "nom_fichier")
    op.drop_column("verifications_casier_judiciaire", "contenu_chiffre")
