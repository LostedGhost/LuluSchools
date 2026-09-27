"""Seed "grandeur nature" de LuluSchools, coherent de bout en bout.

Reinitialise ENTIEREMENT le schema (DROP + CREATE) puis le peuple en rejouant, pour
chaque entite, le workflow reel de la plateforme (voir le paquet seed_donnees/ : chaque
module documente les regles des routeurs qu'il respecte). Verification apres coup :
scripts/verifier_seed.py (invariants metier, lance automatiquement a la fin).

L'Universite d'Abomey-Calavi est TOUJOURS creee, quel que soit --scale.

Usage :
    cd backend
    python scripts/seed_mega.py --yes                  # base de developpement (ENVIRONMENT=development)
    python scripts/seed_mega.py --yes --scale 0.3      # jeu reduit
    python scripts/seed_mega.py --yes --force          # autre base (ex. Render) : voir scripts/seed_render.bat

Options :
    --sans-fichiers        n'envoie aucun fichier a LuluFiles (donnees sans fichier joint)
    --sans-casier-chiffre  les casiers en attente n'ont pas de document : a utiliser quand la
                           cle CASIER_JUDICIAIRE_ENCRYPTION_KEY locale n'est pas celle de la
                           base cible (sinon, document illisible pour l'A+)

Tous les comptes partagent le mot de passe "Password1!" ; les comptes de demonstration
sont imprimes a la fin.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.main  # noqa: F401,E402  (enregistre tous les modeles sur Base.metadata)
from app.core.config import settings  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.modules.etablissements.models import TypeEtablissement  # noqa: E402

from seed_donnees import demo, economie, evaluations, pedagogie, recrutement, scolarite, services, supervision, vie_classe  # noqa: E402
from seed_donnees.contexte import MOT_DE_PASSE_COMMUN, Config, Contexte  # noqa: E402
from seed_donnees.etablissements import creer_etablissements  # noqa: E402
from seed_donnees.fichiers import Fichiers  # noqa: E402


def reset_schema() -> None:
    print("Réinitialisation du schéma (DROP puis CREATE de toutes les tables)...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # create_all ne touche pas alembic_version : on la cale sur head, sinon le prochain
    # `alembic upgrade head` (au demarrage du service) rejouerait toutes les migrations.
    from alembic import command
    from alembic.config import Config as AlembicConfig

    alembic_cfg = AlembicConfig(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.stamp(alembic_cfg, "head", purge=True)
    print("alembic_version calé sur head.")


def executer(ctx: Contexte) -> None:
    db = SessionLocal(expire_on_commit=False)
    try:
        supervision.creer_admin_ministeriel(ctx)
        creer_etablissements(ctx)
        ctx.persister(db)
        n_classes = sum(len(v) for v in ctx.classes_par_etab.values())
        print(f"{len(ctx.etablissements)} établissements, {n_classes} classes.")

        for rang, etab in enumerate(ctx.etablissements, start=1):
            debut = time.monotonic()
            recrutement.recruter_et_affecter(ctx, etab)
            classes = ctx.classes_par_etab[etab.id]
            for classe in classes:
                scolarite.inscrire_classe(ctx, etab, classe)
            if etab.type == TypeEtablissement.UP:
                economie.plafonds(ctx, etab)

            cours_etab, devoirs_etab, devoirs_par_classe = [], [], {}
            for classe in classes:
                cours_etab += pedagogie.creer_cours(ctx, classe)
                devoirs = evaluations.creer_devoirs(ctx, classe)
                devoirs_etab += devoirs
                devoirs_par_classe[classe.id] = devoirs
                evaluations.creer_vie_scolaire(ctx, classe)
                vie_classe.messagerie_classe(ctx, etab, classe, ctx.groupe_par_classe[classe.id])
                vie_classe.sessions_live(ctx, classe)
                pedagogie.el_professor_enseignants(ctx, classe)
                for inscrit in ctx.inscrits_par_classe[classe.id]:
                    pedagogie.el_professor_familles(ctx, inscrit)
            pedagogie.el_professor_eleves(ctx, ctx.inscrits_par_etab[etab.id])
            services.actes(ctx, etab, devoirs_par_classe)
            services.transport_et_cantine(ctx, etab)
            services.billetterie(ctx, etab)
            supervision.moderer_contenus(ctx, cours_etab, devoirs_etab)
            ctx.persister(db)
            print(f"  [{rang}/{len(ctx.etablissements)}] {etab.code_etablissement} {etab.nom} — "
                  f"{len(ctx.inscrits_par_etab[etab.id])} élèves inscrits ({time.monotonic() - debut:.1f} s)")

        print("Marketplace, micro-jobs, Coffre-fort, supervision...")
        economie.marketplace(ctx)
        economie.micro_jobs(ctx)
        supervision.choisir_comptes_demo(ctx)
        demo.garantir(ctx)
        economie.alertes_plafond(ctx)
        supervision.propositions_referentiel(ctx)
        supervision.suspendre(ctx)
        ctx.persister(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def recapitulatif(ctx: Contexte) -> None:
    print("\n" + "═" * 72)
    print("RÉCAPITULATIF")
    print("═" * 72)
    largeur = max(len(k) for k in ctx.compteurs) + 2
    for table, n in sorted(ctx.compteurs.items()):
        print(f"  {table.ljust(largeur)} {n}")
    print(f"  {'fichiers LuluFiles'.ljust(largeur)} {ctx.fichiers.televerses}")
    print("═" * 72)
    print(f"COMPTES DE DÉMONSTRATION — mot de passe commun : {MOT_DE_PASSE_COMMUN}")
    for role, login in ctx.demo.items():
        print(f"  {role.ljust(40)} {login}")
    print("  Chaque établissement a son A+ : admin.<code>@seed.luluschools.example (ex. admin.up01@...).")
    print("═" * 72 + "\n")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="Confirme l'exécution (DROP + CREATE + peuplement).")
    parser.add_argument("--force", action="store_true", help="Autorise une base hors ENVIRONMENT=development.")
    parser.add_argument("--scale", type=float, default=1.0, help="Facteur de volume (défaut 1.0). L'UAC est toujours créée.")
    parser.add_argument("--seed", type=int, default=2026, help="Graine aléatoire (reproductibilité).")
    parser.add_argument("--sans-fichiers", action="store_true", help="N'envoie aucun fichier à LuluFiles.")
    parser.add_argument("--sans-casier-chiffre", action="store_true", help="Casiers en attente sans document chiffré.")
    parser.add_argument("--sans-verification", action="store_true", help="Ne lance pas verifier_seed.py à la fin.")
    args = parser.parse_args()

    cfg = Config(args.scale)
    base = settings.database_url.split("@")[-1]
    print(f"Base ciblée   : {base}")
    print(f"Environnement : {settings.environment}")
    print(f"Échelle {args.scale} : UAC + {cfg.n_ep} EP + {cfg.n_es} ES + {cfg.n_up_autres} autres UP, "
          f"{cfg.eleves_par_classe[0]}-{cfg.eleves_par_classe[1]} élèves par classe.")
    print("\nCE SCRIPT SUPPRIME PUIS RECRÉE TOUTES LES TABLES : toute donnée existante sera DÉFINITIVEMENT PERDUE.\n")
    if settings.environment != "development" and not args.force:
        print("ENVIRONMENT n'est pas 'development' : relancez avec --force si la base ciblée ci-dessus est la bonne.")
        raise SystemExit(1)
    if not args.yes:
        print("Relancez avec --yes pour confirmer.")
        raise SystemExit(1)

    fichiers = Fichiers(actif=not args.sans_fichiers and bool(settings.lulufiles_api_key))
    if fichiers.actif:
        print("Vérification de LuluFiles...")
        fichiers.verifier()
    print(f"Fichiers joints : {'LuluFiles' if fichiers.actif else 'aucun (données sans fichier)'}")

    reset_schema()
    debut = time.monotonic()
    ctx = Contexte(args.seed, cfg, fichiers, casier_chiffrable=not args.sans_casier_chiffre)
    executer(ctx)
    print(f"Seed terminé en {time.monotonic() - debut:.0f} s.")
    recapitulatif(ctx)

    if not args.sans_verification:
        from verifier_seed import verifier

        if not verifier():
            raise SystemExit(2)


if __name__ == "__main__":
    main()
