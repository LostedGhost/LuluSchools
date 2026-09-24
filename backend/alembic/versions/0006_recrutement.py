"""postes, candidatures, documents, casier judiciaire, contestations, contrats

Revision ID: 0006_recrutement
Revises: 0005_enseignants
Create Date: 2026-09-24

"""
import sqlalchemy as sa
from alembic import op

revision = "0006_recrutement"
down_revision = "0005_enseignants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "postes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False),
        sa.Column("titre", sa.String(length=200), nullable=False),
        sa.Column("statut", sa.Enum("OUVERT", "POURVU", "NON_POURVU", name="statutposte"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_postes_etablissement_id", "postes", ["etablissement_id"])

    op.create_table(
        "criteres_document_poste",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("poste_id", sa.String(length=36), sa.ForeignKey("postes.id"), nullable=False),
        sa.Column("type_document", sa.String(length=100), nullable=False),
        sa.Column("coefficient", sa.Float(), nullable=False),
        sa.Column("seuil_minimal", sa.Float(), nullable=False),
    )
    op.create_index("ix_criteres_document_poste_poste_id", "criteres_document_poste", ["poste_id"])

    op.create_table(
        "candidatures",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("poste_id", sa.String(length=36), sa.ForeignKey("postes.id"), nullable=False),
        sa.Column(
            "enseignant_id", sa.String(length=36), sa.ForeignKey("enseignants.utilisateur_id"), nullable=False
        ),
        sa.Column(
            "statut", sa.Enum("EN_EVALUATION", "RETENUE", "REJETEE", name="statutcandidature"), nullable=False
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_candidatures_poste_id", "candidatures", ["poste_id"])
    op.create_index("ix_candidatures_enseignant_id", "candidatures", ["enseignant_id"])

    op.create_table(
        "documents_candidature",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidature_id", sa.String(length=36), sa.ForeignKey("candidatures.id"), nullable=False
        ),
        sa.Column("type_document", sa.String(length=100), nullable=False),
        sa.Column("lulufiles_file_id", sa.String(length=36), nullable=True),
        sa.Column("note_ia", sa.Float(), nullable=True),
        sa.Column(
            "statut",
            sa.Enum("EN_ATTENTE", "NOTE", "ECHEC_NOTATION", name="statutdocument"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_documents_candidature_candidature_id", "documents_candidature", ["candidature_id"]
    )

    op.create_table(
        "verifications_casier_judiciaire",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidature_id", sa.String(length=36), sa.ForeignKey("candidatures.id"), nullable=False
        ),
        sa.Column("chemin_fichier_local", sa.String(length=500), nullable=False),
        sa.Column(
            "statut",
            sa.Enum("EN_ATTENTE", "CONFORME", "NON_CONFORME", name="statutverificationcasier"),
            nullable=False,
        ),
        sa.Column(
            "verifie_par_utilisateur_id", sa.String(length=36), sa.ForeignKey("utilisateurs.id"), nullable=True
        ),
        sa.Column("date_verification", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_suppression_prevue", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_verifications_casier_judiciaire_candidature_id",
        "verifications_casier_judiciaire",
        ["candidature_id"],
    )

    op.create_table(
        "contestations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidature_id", sa.String(length=36), sa.ForeignKey("candidatures.id"), nullable=False
        ),
        sa.Column("motif", sa.Text(), nullable=False),
        sa.Column(
            "statut",
            sa.Enum("EN_ATTENTE", "ACCEPTEE", "REJETEE", name="statutcontestation"),
            nullable=False,
        ),
        sa.Column("motif_decision", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_contestations_candidature_id", "contestations", ["candidature_id"])

    op.create_table(
        "contrats",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidature_id", sa.String(length=36), sa.ForeignKey("candidatures.id"), nullable=False
        ),
        sa.Column(
            "enseignant_id", sa.String(length=36), sa.ForeignKey("enseignants.utilisateur_id"), nullable=False
        ),
        sa.Column(
            "etablissement_id", sa.String(length=36), sa.ForeignKey("etablissements.id"), nullable=False
        ),
        sa.Column("syllabus", sa.Text(), nullable=False),
        sa.Column(
            "statut",
            sa.Enum("EN_ATTENTE_SIGNATURE", "SIGNE", name="statutcontrat"),
            nullable=False,
        ),
        sa.Column("signature_horodatage", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signature_hash_document", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_contrats_candidature_id", "contrats", ["candidature_id"])
    op.create_index("ix_contrats_enseignant_id", "contrats", ["enseignant_id"])
    op.create_index("ix_contrats_etablissement_id", "contrats", ["etablissement_id"])

    op.create_table(
        "propositions_reconduction",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "contrat_precedent_id", sa.String(length=36), sa.ForeignKey("contrats.id"), nullable=False
        ),
        sa.Column("nouveau_contrat_id", sa.String(length=36), sa.ForeignKey("contrats.id"), nullable=True),
        sa.Column(
            "statut",
            sa.Enum("EN_ATTENTE", "ACCEPTEE", "REFUSEE", name="statutproposition"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_propositions_reconduction_contrat_precedent_id",
        "propositions_reconduction",
        ["contrat_precedent_id"],
    )


def downgrade() -> None:
    op.drop_table("propositions_reconduction")
    op.drop_table("contrats")
    op.drop_table("contestations")
    op.drop_table("verifications_casier_judiciaire")
    op.drop_table("documents_candidature")
    op.drop_table("candidatures")
    op.drop_table("criteres_document_poste")
    op.drop_table("postes")
