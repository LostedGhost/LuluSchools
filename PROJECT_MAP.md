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
- Signature du contrat enseignant : tracé dessiné sur canvas (doigt/stylet), signature électronique simple, pas qualifiée — décision définitive de l'utilisateur (ADR-004).

## État d'avancement
Étapes 1-3 du pipeline validées. Étape 4 (backend) : tous les modules de la Phase 1 (UC-01 à UC-10) faits et testés (67 tests), 10 migrations appliquées en réel. Décisions récentes qui ferment d'anciens points ouverts : signature par canvas (ADR-004), moyennes pondérées par les coefficients, quiz généré par IA et devoirs corrigés par IA (formulaires), écrans de révision manuelle, webhook Kkiapay corrigé (URL unique par compte + secret partagé). Détail dans `backend/PROJECT_MAP.md` (§ état d'avancement). Étape 5 (validation de bout en bout) pas encore commencée.

## Dernière synchronisation
2026-09-25 — signature canvas, moyennes pondérées, quiz/formulaires IA, révision manuelle, webhook Kkiapay corrigé.
