"""durcissement securite (audit 2026-09-27)

- utilisateurs.mot_de_passe_modifie_le : les refresh tokens emis avant un changement ou
  une reinitialisation de mot de passe sont refuses.
- otp_verifications.objet : un code de reinitialisation de mot de passe ne peut jamais
  valider une adresse e-mail (et inversement).
- verifications_casier_judiciaire.contenu_chiffre devient nullable : le contenu brut est
  purge des le verdict (ou a l'echeance de retention), seul le statut est conserve
  (Art. 395, loi n. 2017-20).
- candidatures.rejetee_le : le delai de contestation court depuis le rejet, pas depuis
  le depot de la candidature.

Revision ID: 0016_durcissement_securite
Revises: 0015_fusion_lots
Create Date: 2026-09-27 12:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0016_durcissement_securite'
down_revision = '0015_fusion_lots'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('utilisateurs', sa.Column('mot_de_passe_modifie_le', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'otp_verifications',
        sa.Column('objet', sa.String(length=40), nullable=False, server_default='verification_email'),
    )
    op.alter_column('verifications_casier_judiciaire', 'contenu_chiffre', existing_type=sa.LargeBinary(), nullable=True)
    op.add_column('candidatures', sa.Column('rejetee_le', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('candidatures', 'rejetee_le')
    op.execute("UPDATE verifications_casier_judiciaire SET contenu_chiffre = '' WHERE contenu_chiffre IS NULL")
    op.alter_column('verifications_casier_judiciaire', 'contenu_chiffre', existing_type=sa.LargeBinary(), nullable=False)
    op.drop_column('otp_verifications', 'objet')
    op.drop_column('utilisateurs', 'mot_de_passe_modifie_le')
