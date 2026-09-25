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
- Notation/correction IA multi-appels (candidatures, devoirs) exécutée en arrière-plan (`BackgroundTasks`) pour ne jamais bloquer la requête sur la latence de FreeLLM ; génération de quiz (un seul appel) reste synchrone (ADR-005).

## État d'avancement
Étapes 1-5 du pipeline validées pour la Phase 1. Étape 4 (backend) : tous les modules (UC-01 à UC-10) faits et testés (68 tests), 10 migrations appliquées en réel, mot de passe temporaire réellement appliqué côté serveur. Étape 5 (validation de bout en bout) : scénario automatisé rejouant tout le parcours réel dans l'ordre — a révélé et corrigé un vrai bug (chemin du casier judiciaire mal interprété sous Windows). Détail dans `backend/PROJECT_MAP.md`. Prochaine étape : 6 (frontend, page par page).

## Dernière synchronisation
2026-09-25 — durcissement du backend (mot de passe temporaire, délai en jours ouvrés) et validation de bout en bout (étape 5).
