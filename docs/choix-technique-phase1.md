# LuluSchools — Choix technique, étape 3 (méthode lucio-dev)

Raisonnement complet dans `docs/adr/ADR-001-architecture-backend.md` et `docs/adr/ADR-002-integration-llm-freellm.md`. Ce document liste la stack retenue au complet. Contrainte transversale : **pas de Docker** — chaque choix ci-dessous fonctionne en installation native (venv Python, npm, PostgreSQL natif).

## Imposé par l'utilisateur
- Backend : **FastAPI** (Python 3.12)
- Frontend : **React** 18
- Base de données : **PostgreSQL**
- Paiement : **Kkiapay**
- Accès LLM : **FreeLLM** (service personnel de l'utilisateur, API compatible OpenAI) — voir ADR-002

## Backend
- **ORM / migrations** : SQLAlchemy 2.0 + Alembic
- **Validation / config** : Pydantic v2 + `pydantic-settings` (lecture de `.env`)
- **Serveur ASGI** : Uvicorn en dev, Gunicorn (workers Uvicorn) en prod, supervisé par systemd
- **Auth** : JWT (access + refresh) via `python-jose` ; mots de passe hashés en Argon2 (`argon2-cffi`)
- **Accès LLM (notation de documents, UC-04, et tout besoin futur)** : SDK `openai` pointé vers FreeLLM — voir ADR-002
- **Stockage de fichiers** (cours, candidatures hors casier judiciaire, devoirs, actes académiques) : **LuluFiles** (client HTTP `httpx`, un seul disque, stockage à plat) — voir ADR-003. Le casier judiciaire reste sur le système de fichiers local du serveur, accès restreint (Art. 395).
- **Conversion PDF → image** (préalable à l'envoi vision) : `pymupdf` (pip pur, pas de dépendance système)
- **Génération PDF** (bulletins, actes académiques) : `reportlab` — préféré à WeasyPrint qui nécessite Pango/Cairo au niveau système, pénible à installer sur Windows sans Docker pour isoler la dépendance
- **Tâches planifiées** (purge casier judiciaire à 30 jours, rappels d'échéance) : APScheduler in-process
- **Tests** : pytest + httpx (`TestClient`) + pytest-asyncio
- **Paiement** : appels REST directs à l'API Kkiapay + endpoint webhook de confirmation

- **Envoi d'e-mail** (OTP UC-01, et notifications futures) : **Brevo**, API transactionnelle (`POST https://api.brevo.com/v3/smtp/email`, header `api-key`), plan gratuit.

## Points opérationnels encore ouverts (pas bloquants pour coder)
- Prestataire de signature électronique qualifiée (UC-05) — action administrative déjà notée dans `cas-utilisation-phase-1.md`.
- Quota exact du plan gratuit Brevo (nombre d'e-mails/jour) — à vérifier sur le tableau de bord une fois le compte créé, pas documenté publiquement de façon fiable au moment de la rédaction.

## Frontend
- **Build** : Vite + TypeScript
- **Routing** : React Router
- **Style** : Tailwind CSS
- Détails d'architecture (state management, data fetching, structure de dossiers) affinés à l'étape 6 avec le skill `react-architecture`, une fois le backend validé de bout en bout — pas avant, pour respecter l'ordre du pipeline.

## Déploiement (étape 8)
**Révisé par ADR-006** : le plan VPS ci-dessous a été abandonné au profit de deux plateformes managées, sur leurs plans gratuits — Render pour le backend (Web Service Python + PostgreSQL, pas de disque persistant sur ce plan, casier judiciaire chiffré et stocké en base à la place), Vercel pour le frontend (avec rewrite `/api/*` vers Render, pas de CORS côté navigateur). Voir `render.yaml`, `frontend/vercel.json` et `docs/adr/ADR-006-deploiement-render-vercel.md` pour le détail.

~~VPS Linux classique : Nginx en reverse proxy + service de fichiers statiques pour le build React, Gunicorn/Uvicorn pour FastAPI, PostgreSQL natif, systemd pour la supervision des process, Certbot pour le SSL.~~ (plan initial, non retenu)

## Configuration et secrets
Tout secret/paramètre d'environnement passe par `.env` (jamais commité — voir `.gitignore`) ; `.env.example` documente les clés attendues sans valeurs réelles.
