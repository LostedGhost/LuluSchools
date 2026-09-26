# LuluSchools

![Backend CI](https://github.com/LostedGhost/LuluSchools/actions/workflows/backend-ci.yml/badge.svg)
![Frontend CI](https://github.com/LostedGhost/LuluSchools/actions/workflows/frontend-ci.yml/badge.svg)
![Tests backend](https://img.shields.io/badge/tests%20backend-239%20passants-brightgreen)
![Conformité](https://img.shields.io/badge/conformit%C3%A9-loi%20n%C2%B0%202017--20-blue)

**Plateforme éducative nationale, sous mandat ministériel — premier déploiement au Bénin.**
Dématérialise les processus administratifs, pédagogiques, comptables et logistiques du
système éducatif, de la maternelle au supérieur, public comme privé.

Construit avec la méthode spec-first [`lucio-dev`](https://github.com/LostedGhost/LuluSchools) :
chaque étape (cas d'utilisation → UML → choix technique/API → backend → validation → frontend
→ intégration → déploiement) produit un artefact validé avant la suivante — l'IA accélère
l'exécution mais ne décide jamais seule des règles métier, du modèle de données ou de
l'architecture. Avancement réel suivi dans [SUIVI-PROJET.md](SUIVI-PROJET.md), audit complet
des fonctionnalités dans [docs/audit-fonctionnalites-plateforme.md](docs/audit-fonctionnalites-plateforme.md).

## Sommaire

- [Ce que couvre la plateforme](#ce-que-couvre-la-plateforme)
- [Rôles](#rôles)
- [Stack](#stack)
- [Architecture](#architecture-du-dépôt)
- [Développement local](#développement-local-sans-docker)
- [Tests](#tests)
- [Déploiement](#déploiement)
- [Documentation](#documentation)
- [Conformité légale](#conformité-légale)
- [Statut du projet](#statut-du-projet)

## Ce que couvre la plateforme

**58 cas d'utilisation** couverts, organisés en modules cohérents plutôt qu'une liste plate —
détail exhaustif (règles métier, limites assumées, état de validation) dans l'
[audit des fonctionnalités](docs/audit-fonctionnalites-plateforme.md) :

| Domaine | Fonctionnalités |
|---|---|
| **Identité & comptes** | Inscription tuteur/enseignant, OTP e-mail, JWT access+refresh, RBAC centralisé, suspension de compte |
| **Établissements** | Classes avec année académique, rentrée scolaire, affectation enseignant↔classe, annuaire public, photos |
| **Parcours élève** | Inscription (consentement parental Art. 446), matricule national généré, politique de capacité |
| **Recrutement** | Postes, formulaire de candidature dynamique, notation de documents par IA, casier judiciaire chiffré, contrat signé par tracé canvas |
| **Pédagogie** | Cours (texte/PDF/audio/vidéo), quiz généré par IA, vie scolaire, sessions en direct avec tableau collaboratif temps réel |
| **Évaluations** | Devoirs formatifs/sommatifs, soumission texte ou copie photographiée corrigée par IA, référentiels de coefficients, bulletins pondérés |
| **El Professor** | Assistant IA à 4 personas (élève, enseignant, tuteur, famille), garde-fou de sécurité avec alerte administrative |
| **Actes académiques** | Catalogue par établissement, demande et traitement, paiement Kkiapay |
| **Vie extra-scolaire** | Transport/cantine, billetterie d'événements, visites virtuelles 3D/drone, ticketerie unifiée avec QR codes |
| **Économie étudiante** | Marketplace et micro-jobs réservés aux étudiants majeurs, séquestre de paiement, arbitrage de contestations |
| **Innovations familiales** | Coffre-fort familial (validation parentale des dépenses), Radar familial (digest hebdomadaire), Passeport de compétences exportable |
| **Gouvernance** | Console admin établissement multi-modules, supervision transverse nationale, journal d'audit ministériel |

## Rôles

5 rôles permanents (**Tuteur**, **Élève/Étudiant**, **Enseignant**, **Admin établissement A+**,
**Admin ministériel A++**) et 3 rôles temporaires attribués sans créer de nouveau compte
(**Contrôleur/Ticketeur**, **Parrain d'événement**, **Prestataire micro-job**).

## Stack

- **Backend** : FastAPI (Python 3.13), SQLAlchemy 2.0 + Alembic, PostgreSQL
- **Frontend** : React 19 + Vite + TypeScript, Tailwind CSS v4
- **Paiement** : Kkiapay (widget + webhook unique pour tout le compte)
- **IA** : [FreeLLM](https://github.com/LostedGhost/freellm-lucio), API compatible OpenAI — notation de documents, génération de quiz, correction de devoirs, assistant El Professor, résumés de session live, digest familial
- **Stockage de fichiers** : [LuluFiles](https://lulufiles-api.onrender.com) pour tout document sauf le casier judiciaire, chiffré et gardé en base pour raisons légales (Art. 395)
- **Déploiement** : Render (backend + PostgreSQL, plan gratuit) et Vercel ou Netlify (frontend) — voir [docs/deploiement-render-vercel.md](docs/deploiement-render-vercel.md) et [ADR-006](docs/adr/ADR-006-deploiement-render-vercel.md)
- **CI/CD** : GitHub Actions (tests + lint + build sur chaque push/PR, `.github/workflows/`) ; le déploiement lui-même reste géré nativement par Render et Vercel (redéploiement automatique sur push `main`)

Détail complet et justification des choix : [docs/choix-technique-phase1.md](docs/choix-technique-phase1.md) et les 9 [ADR](docs/adr/).

## Architecture du dépôt

```
LuluSchools/
├── backend/            API FastAPI (monolithe modulaire, un module = models+schemas+router)
│   ├── app/modules/    21 modules métier (identité, établissements, pédagogie, coffre_fort, ...)
│   ├── alembic/        migrations, une par évolution de schéma
│   ├── scripts/        seed_admin_ministeriel.py, seed_mega.py (jeu de données grandeur nature)
│   ├── tests/          pytest, SQLite en mémoire, tous les services externes mockés
│   └── PROJECT_MAP.md  carte détaillée du backend (fichier par fichier)
├── frontend/           application React (Vite/TS/Tailwind), une page par écran, par rôle
│   ├── src/pages/      tuteur/, eleve/, enseignant/, admin_etablissement/, admin_ministeriel/
│   └── PROJECT_MAP.md  carte détaillée du frontend
├── docs/               cas d'utilisation, diagrammes UML, contrats d'API, ADR, déploiement
└── PROJECT_MAP.md      vue d'ensemble du dépôt (celle que vous lisez en creux dans ce README)
```

Chaque `PROJECT_MAP.md` est tenu à jour à chaque lot livré — c'est la référence pour reprendre
le projet sans relire tout le code.

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

Dans un second terminal :

```bash
cd frontend
cp .env.example .env   # renseigner VITE_KKIAPAY_PUBLIC_KEY
npm install
npm run dev              # démarre le frontend sur http://localhost:5173 (proxy /api vers le backend local)
```

Pour peupler la base locale avec un jeu de données réaliste (~30 établissements, ~6200
comptes, toutes les tables applicatives) plutôt que de créer des comptes un par un :

```bash
cd backend
python scripts/seed_mega.py --yes   # --scale ajuste le volume, --seed change le tirage aléatoire
```

Tous les comptes générés partagent le mot de passe `Password1!`.

## Tests

```bash
cd backend && pytest                 # suite backend (aucune dépendance externe, tout est mocké)
cd frontend && npx tsc -b            # vérification de types
cd frontend && npx vite build        # build de production
cd frontend && npx oxlint            # lint
```

Chaque lot de fonctionnalités a été validé de bout en bout (`test_e2e_parcours_*.py`, un seul
jeu d'objets rejouant le parcours réel dans l'ordre) avant d'être considéré terminé — voir le
détail par phase dans l'[audit des fonctionnalités](docs/audit-fonctionnalites-plateforme.md#4-état-de-validation-par-lot).

## Déploiement

Backend sur Render (Blueprint `render.yaml`, Web Service + PostgreSQL, plan gratuit) et
frontend sur Vercel ou Netlify (configs équivalentes, `frontend/vercel.json` /
`frontend/netlify.toml`) — redéploiement automatique sur chaque push `main`. Marche à suivre
complète : [docs/deploiement-render-vercel.md](docs/deploiement-render-vercel.md).

## Documentation

| Document | Contenu |
|---|---|
| [docs/audit-fonctionnalites-plateforme.md](docs/audit-fonctionnalites-plateforme.md) | Audit complet des fonctionnalités, par domaine, avec état de validation et limites connues |
| [SUIVI-PROJET.md](SUIVI-PROJET.md) | Avancement du pipeline en 8 étapes, cadrage verrouillé |
| [docs/cas-utilisation-phase-1.md](docs/cas-utilisation-phase-1.md) | Cas d'utilisation validés de la Phase 1, avec règles métier et références légales |
| [docs/diagrammes-uml-phase1.md](docs/diagrammes-uml-phase1.md) | Diagramme de cas d'utilisation et diagrammes de classes |
| [docs/choix-technique-phase1.md](docs/choix-technique-phase1.md) | Stack technique complète |
| [docs/contrat-api-phase1.md](docs/contrat-api-phase1.md) | Contrat d'API (ressources, méthodes, conventions) |
| [docs/cas-utilisation-phase-2-3.md](docs/cas-utilisation-phase-2-3.md) | Cas d'utilisation Phase 2/3 (UC-11 à UC-19) |
| [docs/diagrammes-uml-phase2-3.md](docs/diagrammes-uml-phase2-3.md) | Diagrammes UML Phase 2/3 |
| [docs/contrat-api-phase2-3.md](docs/contrat-api-phase2-3.md) | Contrat d'API Phase 2/3 |
| [docs/cas-utilisation-phase-4-marketplace.md](docs/cas-utilisation-phase-4-marketplace.md) | Cas d'utilisation Phase 4 — marketplace étudiante (UC-20 à UC-22) |
| [docs/diagrammes-uml-phase-4-marketplace.md](docs/diagrammes-uml-phase-4-marketplace.md) | Diagrammes UML Phase 4 — marketplace étudiante |
| [docs/contrat-api-phase-4-marketplace.md](docs/contrat-api-phase-4-marketplace.md) | Contrat d'API Phase 4 — marketplace étudiante |
| [docs/cahier-des-charges-refonte-admin-ministeriel.md](docs/cahier-des-charges-refonte-admin-ministeriel.md) | Cas d'utilisation — refonte du portail admin ministériel |
| [docs/diagrammes-uml-phase-5-admin-ministeriel.md](docs/diagrammes-uml-phase-5-admin-ministeriel.md) | Diagrammes UML (contrat d'API fusionné dans le même document) |
| [docs/cahier-des-charges-refonte-admin-etablissement.md](docs/cahier-des-charges-refonte-admin-etablissement.md) | Cas d'utilisation — refonte du portail admin établissement (UC-39 à UC-58) |
| [docs/diagrammes-uml-phase-6-admin-etablissement.md](docs/diagrammes-uml-phase-6-admin-etablissement.md) | Diagrammes UML (contrat d'API fusionné dans le même document) |
| [docs/adr/](docs/adr/) | 9 décisions d'architecture (ADR), chacune justifiée et datée |
| [docs/deploiement-render-vercel.md](docs/deploiement-render-vercel.md) | Étapes de déploiement (Render + Vercel) |
| [backend/PROJECT_MAP.md](backend/PROJECT_MAP.md) | Carte détaillée du backend, fichier par fichier |
| [frontend/PROJECT_MAP.md](frontend/PROJECT_MAP.md) | Carte détaillée du frontend, fichier par fichier |

## Conformité légale

Premier déploiement au Bénin : conformité suivie article par article contre la loi n° 2017-20
(Code du numérique), en particulier :

- **Art. 446** — protection des mineurs : branche d'âge à l'inscription, micro-jobs/marketplace réservés aux étudiants majeurs numériques
- **Art. 389-390** — consentement parental horodaté et démontrable
- **Art. 395** — données sensibles (casier judiciaire) chiffrées et gardées en base, jamais confiées à un stockage tiers
- **Art. 284-287** — signature électronique simple (tracé canvas) pour les contrats enseignants
- **Art. 401** — aucune décision automatisée par IA sans recours humain (écran de révision manuelle systématique)
- **Art. 354/356** — bornes de remboursement précises (transport/cantine, billetterie)

## Statut du projet

**239 tests backend passants**, `tsc -b` + `vite build` + `oxlint` au vert côté frontend.
6 lots livrés (Phase 1 → Phase 6 + volets Professeur et Élève/Tuteur), détail complet et
limites connues dans l'[audit des fonctionnalités](docs/audit-fonctionnalites-plateforme.md).
