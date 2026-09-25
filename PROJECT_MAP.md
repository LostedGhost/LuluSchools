# LuluSchools — Project Map

## Identité
Plateforme éducative nationale sous mandat ministériel (Bénin). Backend FastAPI/PostgreSQL, frontend React (Vite/TS/Tailwind) — parcours Tuteur/Élève fonctionnel et intégré au backend réel. Développé avec la méthode spec-first `lucio-dev`. Cahier des charges : `docs/cas-utilisation-phase-1.md`, diagrammes : `docs/diagrammes-uml-phase1.md`, décisions d'architecture : `docs/adr/`, avancement du pipeline : `SUIVI-PROJET.md`.

## Arborescence
- `backend/` — API FastAPI (monolithe modulaire) — voir `backend/PROJECT_MAP.md`
- `docs/` — spec, UML, ADR, contrat d'API
- `frontend/` — application React (Vite/TS/Tailwind) — voir `frontend/PROJECT_MAP.md`. Parcours Tuteur et Élève construits et testés en navigateur contre le backend réel ; Enseignant/A+/A++ restent à faire.

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
Étapes 1-5 du pipeline validées pour la Phase 1. Étape 4 (backend) : tous les modules (UC-01 à UC-10) faits et testés (71 tests), 12 migrations appliquées en réel, mot de passe temporaire réellement appliqué côté serveur, notation/correction IA en arrière-plan (ADR-005). Étape 5 (validation de bout en bout) : scénario automatisé rejouant tout le parcours réel dans l'ordre — a révélé et corrigé un vrai bug (chemin du casier judiciaire mal interprété sous Windows). Étape 6 (frontend) : **parcours Tuteur/Élève complet et testé en navigateur reel contre le backend reel** (pas de mocks) — inscription, consentement parental, tableau de bord tuteur, dashboard élève, cours, quiz généré par IA (pris et noté), devoir corrigé par IA en arrière-plan (soumis et suivi jusqu'au résultat), bulletin pondéré, réclamation de note. Ce test manuel a révélé et corrigé un second vrai bug (`DocumentCandidatureOut` sans `id`, écran de révision manuelle inutilisable). Restent à construire côté frontend : Enseignant, A+ (admin établissement), A++ (admin ministériel), et les écrans de révision manuelle. Détail dans `backend/PROJECT_MAP.md` et `frontend/PROJECT_MAP.md`.

## Dernière synchronisation
2026-09-25 — parcours Tuteur/Élève du frontend construit et validé de bout en bout contre le backend réel (étape 6, en cours).
