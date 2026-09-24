"""cours, quiz, devoirs, soumissions, referentiels, bulletins, actes academiques

Revision ID: 0008_pedagogie_evaluations_actes
Revises: 0007_contrats_date_fin
Create Date: 2026-09-24

"""
import sqlalchemy as sa
from alembic import op

revision = "0008_pedagogie_evaluations_actes"
down_revision = "0007_contrats_date_fin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cours",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("classe_id", sa.String(length=36), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column(
            "enseignant_id", sa.String(length=36), sa.ForeignKey("enseignants.utilisateur_id"), nullable=False
        ),
        sa.Column("titre", sa.String(length=200), nullable=False),
        sa.Column("chapitre", sa.String(length=200), nullable=False),
        sa.Column("format", sa.Enum("TEXTE", "PDF", "AUDIO", name="formatcours"), nullable=False),
        sa.Column("contenu_texte", sa.Text(), nullable=True),
        sa.Column("lulufiles_file_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cours_classe_id", "cours", ["classe_id"])
    op.create_index("ix_cours_enseignant_id", "cours", ["enseignant_id"])

    op.create_table(
        "quiz",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("cours_id", sa.String(length=36), sa.ForeignKey("cours.id"), nullable=False),
        sa.Column("seuil_reussite", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quiz_cours_id", "quiz", ["cours_id"])

    op.create_table(
        "tentatives_quiz",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("quiz_id", sa.String(length=36), sa.ForeignKey("quiz.id"), nullable=False),
        sa.Column("eleve_id", sa.String(length=36), sa.ForeignKey("eleves.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reussie", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tentatives_quiz_quiz_id", "tentatives_quiz", ["quiz_id"])
    op.create_index("ix_tentatives_quiz_eleve_id", "tentatives_quiz", ["eleve_id"])

    op.create_table(
        "devoirs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("classe_id", sa.String(length=36), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column(
            "enseignant_id", sa.String(length=36), sa.ForeignKey("enseignants.utilisateur_id"), nullable=False
        ),
        sa.Column("titre", sa.String(length=200), nullable=False),
        sa.Column("date_limite", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bareme", sa.Enum("RIGIDE", "FLEXIBLE", name="baremedevoir"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_devoirs_classe_id", "devoirs", ["classe_id"])
    op.create_index("ix_devoirs_enseignant_id", "devoirs", ["enseignant_id"])

    op.create_table(
        "soumissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("devoir_id", sa.String(length=36), sa.ForeignKey("devoirs.id"), nullable=False),
        sa.Column("eleve_id", sa.String(length=36), sa.ForeignKey("eleves.id"), nullable=False),
        sa.Column("lulufiles_file_id", sa.String(length=36), nullable=True),
        sa.Column("note", sa.Float(), nullable=True),
        sa.Column("statut", sa.Enum("A_TEMPS", "CORRIGEE", name="statutsoumission"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_soumissions_devoir_id", "soumissions", ["devoir_id"])
    op.create_index("ix_soumissions_eleve_id", "soumissions", ["eleve_id"])

    op.create_table(
        "referentiels_coefficients",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("niveau", sa.String(length=100), nullable=False),
        sa.Column("matiere", sa.String(length=100), nullable=False),
        sa.Column("coefficient", sa.Float(), nullable=False),
        sa.Column(
            "statut",
            sa.Enum("VALIDE", "PROPOSITION_EN_ATTENTE", "REMPLACE", name="statutreferentiel"),
            nullable=False,
        ),
        sa.Column(
            "etablissement_proposant_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=True
        ),
        sa.Column(
            "propose_pour_id", sa.String(length=36), sa.ForeignKey("referentiels_coefficients.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "bulletins",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("eleve_id", sa.String(length=36), sa.ForeignKey("eleves.id"), nullable=False),
        sa.Column("classe_id", sa.String(length=36), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("periode", sa.String(length=50), nullable=False),
        sa.Column("moyenne_generale", sa.Float(), nullable=False),
        sa.Column("decision_passage", sa.String(length=50), nullable=True),
        sa.Column("valide_par_conseil", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bulletins_eleve_id", "bulletins", ["eleve_id"])
    op.create_index("ix_bulletins_classe_id", "bulletins", ["classe_id"])

    op.create_table(
        "types_acte_academique",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("prix", sa.Float(), nullable=False),
        sa.Column("pieces_requises", sa.Text(), nullable=False),
        sa.Column("condition_eligibilite", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_types_acte_academique_etablissement_id", "types_acte_academique", ["etablissement_id"])

    op.create_table(
        "demandes_acte_academique",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("eleve_id", sa.String(length=36), sa.ForeignKey("eleves.id"), nullable=False),
        sa.Column(
            "type_acte_id", sa.String(length=36), sa.ForeignKey("types_acte_academique.id"), nullable=True
        ),
        sa.Column("est_reclamation", sa.Boolean(), nullable=False),
        sa.Column("reference_evaluation", sa.String(length=200), nullable=True),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column(
            "statut",
            sa.Enum("SOUMISE", "EN_TRAITEMENT", "ACCEPTEE", "REJETEE", name="statutdemandeacte"),
            nullable=False,
        ),
        sa.Column("paiement_confirme", sa.Boolean(), nullable=False),
        sa.Column("motif_rejet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_demandes_acte_academique_eleve_id", "demandes_acte_academique", ["eleve_id"])


def downgrade() -> None:
    op.drop_table("demandes_acte_academique")
    op.drop_table("types_acte_academique")
    op.drop_table("bulletins")
    op.drop_table("referentiels_coefficients")
    op.drop_table("soumissions")
    op.drop_table("devoirs")
    op.drop_table("tentatives_quiz")
    op.drop_table("quiz")
    op.drop_table("cours")
