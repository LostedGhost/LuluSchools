# LuluSchools

Plateforme éducative nationale (maternelle à supérieur, public et privé), sous mandat ministériel, premier déploiement au Bénin. Dématérialisation des processus administratifs, pédagogiques, comptables et logistiques du système éducatif.

Construit avec la méthode spec-first [`lucio-dev`](https://github.com/LostedGhost/LuluSchools) : chaque étape (cas d'utilisation → UML → choix technique/API → backend → validation → frontend → intégration → déploiement) produit un artefact validé avant la suivante. L'avancement réel est suivi dans [SUIVI-PROJET.md](SUIVI-PROJET.md).

## Stack

- **Backend** : FastAPI (Python 3.12), SQLAlchemy 2.0 + Alembic, PostgreSQL
- **Frontend** : React 18 + Vite + TypeScript, Tailwind CSS
- **Paiement** : Kkiapay
- **Accès LLM** (notation automatique de documents, etc.) : [FreeLLM](https://github.com/LostedGhost/freellm-lucio), API compatible OpenAI
- **Stockage de fichiers** : [LuluFiles](https://lulufiles-api.onrender.com) pour tout document sauf le casier judiciaire (resté local pour raisons légales, Art. 395)
- **Déploiement** : VPS classique sans conteneurs — Nginx + Gunicorn/Uvicorn + systemd + PostgreSQL natif

Détail complet et justification des choix : [docs/choix-technique-phase1.md](docs/choix-technique-phase1.md) et les ADR dans [docs/adr/](docs/adr/).

## Documentation

| Document | Contenu |
|---|---|
| [SUIVI-PROJET.md](SUIVI-PROJET.md) | Avancement du pipeline en 8 étapes, cadrage verrouillé |
| [docs/cas-utilisation-phase-1.md](docs/cas-utilisation-phase-1.md) | Cas d'utilisation validés de la Phase 1, avec règles métier et références légales |
| [docs/diagrammes-uml-phase1.md](docs/diagrammes-uml-phase1.md) | Diagramme de cas d'utilisation et diagrammes de classes |
| [docs/choix-technique-phase1.md](docs/choix-technique-phase1.md) | Stack technique complète |
| [docs/contrat-api-phase1.md](docs/contrat-api-phase1.md) | Contrat d'API (ressources, méthodes, conventions) |
| [docs/adr/](docs/adr/) | Décisions d'architecture (ADR) |

## Conformité

Premier déploiement au Bénin : conformité suivie article par article contre la loi n° 2017-20 (Code du numérique), en particulier sur la protection des données des mineurs (Art. 446), le consentement (Art. 389-390), la signature électronique (Art. 284-287) et l'interdiction des décisions automatisées sans recours (Art. 401).

## Développement local (sans Docker)

Prérequis : Python 3.12+ (testé avec 3.13), Node.js 20+, PostgreSQL installé nativement.

```bash
cp .env.example .env
# renseigner .env avec les vraies valeurs

cd backend
python -m venv .venv
./.venv/Scripts/activate   # ou source .venv/bin/activate sous Linux/macOS
pip install -r requirements.txt
alembic upgrade head         # applique les migrations sur la base PostgreSQL configurée dans .env
pytest                       # lance la suite de tests (base SQLite en mémoire, aucune dépendance externe)
uvicorn app.main:app --reload   # démarre l'API sur http://localhost:8000
```

Le frontend n'existe pas encore (étape 6 du pipeline, après validation complète du backend).

## Statut

Étapes 1 (cas d'utilisation), 2 (UML) et 3 (choix technique et contrat d'API) validées. Étape 4 (backend) : premier jet complet de tous les modules de la Phase 1 (identité, établissements, inscriptions, recrutement/contrats, pédagogie, évaluations, actes académiques) — 60 tests passants, 8 migrations appliquées. Limitations et points ouverts documentés dans [backend/PROJECT_MAP.md](backend/PROJECT_MAP.md) et [docs/contrat-api-phase1.md](docs/contrat-api-phase1.md) (le plus important : signature électronique qualifiée UC-05 en attente d'un prestataire, remplacée par une signature simple pour l'instant). Étape 5 (validation de bout en bout) pas encore commencée.
