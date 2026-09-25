"""devoirs/soumissions en formulaires corriges par IA, quiz generes par IA, paiement kkiapay

Revision ID: 0010_formulaires_evaluation_et_quiz_llm
Revises: 0009_contrats_signature_image
Create Date: 2026-09-25

Aucune donnee reelle n'existe encore dans devoirs/soumissions/quiz/tentatives_quiz
(jamais exercitees via l'API reelle, seulement via la suite de tests SQLite) : cette
migration recree soumissions plutot que de tenter une modification d'enum Postgres en
place. Ne pas reproduire ce pattern une fois des donnees reelles presentes.
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_formulaires_llm"
down_revision = "0009_contrats_signature_image"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- devoirs : ajout de la matiere (necessaire a la ponderation par coefficient) ---
    op.add_column("devoirs", sa.Column("matiere", sa.String(length=100), nullable=False, server_default="generale"))
    op.alter_column("devoirs", "matiere", server_default=None)

    op.create_table(
        "questions_devoir",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("devoir_id", sa.String(length=36), sa.ForeignKey("devoirs.id"), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.Column("enonce", sa.Text(), nullable=False),
        sa.Column("bareme_reponse", sa.Text(), nullable=False),
        sa.Column("points_max", sa.Float(), nullable=False),
    )
    op.create_index("ix_questions_devoir_devoir_id", "questions_devoir", ["devoir_id"])

    # --- soumissions : recreee (formulaire de reponses, plus de fichier joint) ---
    op.drop_table("soumissions")
    op.execute("DROP TYPE statutsoumission")
    op.create_table(
        "soumissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("devoir_id", sa.String(length=36), sa.ForeignKey("devoirs.id"), nullable=False),
        sa.Column("eleve_id", sa.String(length=36), sa.ForeignKey("eleves.id"), nullable=False),
        sa.Column("note", sa.Float(), nullable=True),
        sa.Column(
            "statut", sa.Enum("CORRIGEE", "ECHEC_CORRECTION", name="statutsoumission"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_soumissions_devoir_id", "soumissions", ["devoir_id"])
    op.create_index("ix_soumissions_eleve_id", "soumissions", ["eleve_id"])

    op.create_table(
        "reponses_soumission",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("soumission_id", sa.String(length=36), sa.ForeignKey("soumissions.id"), nullable=False),
        sa.Column("question_id", sa.String(length=36), sa.ForeignKey("questions_devoir.id"), nullable=False),
        sa.Column("texte_reponse", sa.Text(), nullable=False),
        sa.Column("points_obtenus", sa.Float(), nullable=True),
        sa.Column("commentaire_ia", sa.Text(), nullable=True),
    )
    op.create_index("ix_reponses_soumission_soumission_id", "reponses_soumission", ["soumission_id"])
    op.create_index("ix_reponses_soumission_question_id", "reponses_soumission", ["question_id"])

    # --- quiz : questions generees par le LLM ---
    op.create_table(
        "questions_quiz",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("quiz_id", sa.String(length=36), sa.ForeignKey("quiz.id"), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.Column("enonce", sa.Text(), nullable=False),
        sa.Column("choix", sa.JSON(), nullable=False),
        sa.Column("reponse_correcte_index", sa.Integer(), nullable=False),
    )
    op.create_index("ix_questions_quiz_quiz_id", "questions_quiz", ["quiz_id"])

    op.add_column("tentatives_quiz", sa.Column("reponses", sa.JSON(), nullable=True))
    op.execute("UPDATE tentatives_quiz SET reponses = '[]'")
    op.alter_column("tentatives_quiz", "reponses", nullable=False)

    # --- actes academiques : rattachement a une transaction Kkiapay ---
    op.add_column(
        "demandes_acte_academique", sa.Column("kkiapay_transaction_id", sa.String(length=100), nullable=True)
    )
    op.create_index(
        "ix_demandes_acte_academique_kkiapay_transaction_id",
        "demandes_acte_academique",
        ["kkiapay_transaction_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_demandes_acte_academique_kkiapay_transaction_id", table_name="demandes_acte_academique")
    op.drop_column("demandes_acte_academique", "kkiapay_transaction_id")

    op.drop_column("tentatives_quiz", "reponses")
    op.drop_table("questions_quiz")

    op.drop_table("reponses_soumission")
    op.drop_table("soumissions")
    op.execute("DROP TYPE statutsoumission")
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

    op.drop_table("questions_devoir")
    op.drop_column("devoirs", "matiere")
