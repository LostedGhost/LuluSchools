"""limitation de debit en base et alignement du schema sur les modeles

- tentatives_limitees : compteurs de la limitation de debit (valables multi-workers).
- Types enum renommes comme les modeles (origineelalerteelprofessor, faute de frappe ;
  nature_entree_vie_scolaire).
- Unicite exprimee par un index unique (comme les modeles) plutot que par une contrainte
  doublee d'un index simple, sur trois colonnes.

Revision ID: 0017_limitation_debit
Revises: 0016_durcissement_securite
Create Date: 2026-09-27 15:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0017_limitation_debit'
down_revision = '0016_durcissement_securite'
branch_labels = None
depends_on = None

_UNICITES = [
    ("resumes_session_live", "session_id"),
    ("plafonds_familiaux", "eleve_utilisateur_id"),
    ("contestations_marketplace", "transaction_id"),
]


# Idempotente (incident de deploiement du 2026-09-28) : une base peut avoir ete
# reconstruite depuis les modeles (Base.metadata.create_all, ancien seed) puis timbree a
# une revision anterieure. Elle contient alors DEJA l'etat vise ici (types enum aux noms
# des modeles, index uniques, parfois la table) a cote des vestiges de 0001. Chaque etape
# constate donc l'etat reel avant d'agir, au lieu de supposer une base issue des seules
# migrations.

# (ancien nom, nom des modeles, table, colonne qui l'utilise)
_TYPES = [
    ("origineelalerteelprofessor", "originealerteelprofessor", "alertes_el_professor", "origine"),
    ("nature_entree_vie_scolaire", "natureentreeviescolaire", "entrees_vie_scolaire", "nature"),
]


def _scalaire(sql: str, **params):
    return op.get_bind().execute(sa.text(sql), params).scalar()


def _type_existe(nom: str) -> bool:
    return bool(_scalaire("SELECT 1 FROM pg_type WHERE typname = :n AND typtype = 'e'", n=nom))


def _aligner_type(ancien: str, cible: str, table: str, colonne: str) -> None:
    if not _type_existe(ancien):
        return  # deja aligne
    if not _type_existe(cible):
        op.execute(f"ALTER TYPE {ancien} RENAME TO {cible}")
        return
    # Les deux types coexistent : la colonne passe sur le type des modeles (en y ajoutant
    # d'abord les valeurs qui lui manqueraient), puis l'ancien type, orphelin, est supprime.
    utilise = _scalaire(
        "SELECT udt_name FROM information_schema.columns WHERE table_name = :t AND column_name = :c",
        t=table, c=colonne,
    )
    if utilise == ancien:
        cible_utilise = _scalaire("SELECT count(*) FROM information_schema.columns WHERE udt_name = :c", c=cible)
        if not cible_utilise:
            # Type des modeles present mais inutilise : on le remplace par l'ancien, renomme
            # (toutes les valeurs deja stockees restent valides, aucune conversion).
            op.execute(f"DROP TYPE {cible}")
            op.execute(f"ALTER TYPE {ancien} RENAME TO {cible}")
            return
        manquantes = op.get_bind().execute(sa.text(
            "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = :a "
            "EXCEPT SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = :c"
        ), {"a": ancien, "c": cible}).scalars().all()
        for valeur in manquantes:
            op.execute(f"ALTER TYPE {cible} ADD VALUE IF NOT EXISTS '{valeur}'")
        # Une valeur par defaut typee sur l'ancien enum bloque la conversion : on la retire
        # le temps du changement de type, puis on la remet, typee sur le nouvel enum.
        defaut = _scalaire(
            "SELECT column_default FROM information_schema.columns WHERE table_name = :t AND column_name = :c",
            t=table, c=colonne,
        )
        if defaut:
            op.execute(f"ALTER TABLE {table} ALTER COLUMN {colonne} DROP DEFAULT")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {colonne} TYPE {cible} USING {colonne}::text::{cible}")
        if defaut:
            op.execute(f"ALTER TABLE {table} ALTER COLUMN {colonne} SET DEFAULT {defaut.replace(ancien, cible)}")
    op.execute(f"DROP TYPE {ancien}")


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS tentatives_limitees ("
        "id VARCHAR(36) PRIMARY KEY, cle VARCHAR(255) NOT NULL, created_at TIMESTAMP WITH TIME ZONE NOT NULL)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_tentatives_limitees_cle ON tentatives_limitees (cle)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tentatives_limitees_created_at ON tentatives_limitees (created_at)")

    for ancien, cible, table, colonne in _TYPES:
        _aligner_type(ancien, cible, table, colonne)

    for table, colonne in _UNICITES:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_{colonne}_key")
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_{colonne}")
        op.execute(f"CREATE UNIQUE INDEX ix_{table}_{colonne} ON {table} ({colonne})")


def downgrade() -> None:
    for table, colonne in _UNICITES:
        op.drop_index(f"ix_{table}_{colonne}", table_name=table)
        op.create_index(f"ix_{table}_{colonne}", table, [colonne], unique=False)
        op.create_unique_constraint(f"{table}_{colonne}_key", table, [colonne])

    op.execute("ALTER TYPE natureentreeviescolaire RENAME TO nature_entree_vie_scolaire")
    op.execute("ALTER TYPE originealerteelprofessor RENAME TO origineelalerteelprofessor")

    op.drop_index('ix_tentatives_limitees_created_at', table_name='tentatives_limitees')
    op.drop_index('ix_tentatives_limitees_cle', table_name='tentatives_limitees')
    op.drop_table('tentatives_limitees')
