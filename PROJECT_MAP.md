# LuluSchools — Project Map

## Identité
Plateforme éducative nationale sous mandat ministériel (Bénin). Backend FastAPI/PostgreSQL, frontend React (pas encore commencé). Développé avec la méthode spec-first `lucio-dev`. Cahier des charges : `docs/cas-utilisation-phase-1.md`, diagrammes : `docs/diagrammes-uml-phase1.md`, décisions d'architecture : `docs/adr/`, avancement du pipeline : `SUIVI-PROJET.md`.

## Arborescence
- `backend/` — API FastAPI (monolithe modulaire) — voir `backend/PROJECT_MAP.md`
- `docs/` — spec, UML, ADR, contrat d'API
- `frontend/` — pas encore créé (étape 6 du pipeline, après validation complète du backend)

## Points d'entrée
API backend sous préfixe `/api/v1` — contrat complet et à jour dans `docs/contrat-api-phase1.md`, ne pas le dupliquer ici.

## Conventions
- Pas de Docker (ADR-001) : venv Python natif, PostgreSQL natif, déploiement VPS prévu (Nginx + Gunicorn/Uvicorn + systemd).
- Toute décision d'architecture structurante devient un ADR dans `docs/adr/`, jamais seulement actée en conversation.
- Un commit par artefact/endpoint livré (voir historique git) — pas de gros commits fourre-tout.

## Décisions d'architecture notables
- Monolithe modulaire, pas de microservices (ADR-001).
- Accès LLM (notation de documents, etc.) exclusivement via FreeLLM (service personnel, API compatible OpenAI), jamais l'API Anthropic en direct (ADR-002).
- Stockage de fichiers via LuluFiles, sauf le casier judiciaire qui reste local pour raisons légales — Art. 395 de la loi béninoise n° 2017-20 (ADR-003).

## État d'avancement
Étapes 1-3 du pipeline validées. Étape 4 (backend) en cours : identité, établissements/classes, inscriptions et recrutement (UC-01 à UC-05 partiel) faits et testés (46 tests). Reste : pédagogie, évaluations, actes académiques ; signature qualifiée (UC-05) et reconduction (UC-05b) en attente.

## Dernière synchronisation
2026-09-24 — après le module recrutement.
