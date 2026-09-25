# LuluSchools — Project Map

## Identité
Plateforme éducative nationale sous mandat ministériel (Bénin). Backend FastAPI/PostgreSQL, frontend React (Vite/TS/Tailwind) — les 5 rôles de la Phase 1 (Tuteur, Élève, Enseignant, A+, A++) sont fonctionnels et intégrés au backend réel. Développé avec la méthode spec-first `lucio-dev`. Cahier des charges Phase 1 : `docs/cas-utilisation-phase-1.md` ; Phases 2/3 (cas d'utilisation + UML validés, contrat d'API en cours) : `docs/cas-utilisation-phase-2-3.md`, `docs/diagrammes-uml-phase2-3.md`, `docs/contrat-api-phase2-3.md`. Décisions d'architecture : `docs/adr/`, avancement du pipeline : `SUIVI-PROJET.md`.

## Arborescence
- `backend/` — API FastAPI (monolithe modulaire) — voir `backend/PROJECT_MAP.md`
- `docs/` — spec, UML, ADR, contrat d'API
- `frontend/` — application React (Vite/TS/Tailwind) — voir `frontend/PROJECT_MAP.md`. Les 5 rôles de la Phase 1 sont construits et testés en navigateur contre le backend réel (pas de mocks) : Tuteur, Élève, Enseignant, A+ (admin établissement), A++ (admin ministériel).
- `render.yaml` — Blueprint de déploiement du backend sur Render (Web Service + PostgreSQL + disque persistant pour le casier judiciaire) — voir ADR-006 et `docs/deploiement-render-vercel.md`.
- `frontend/vercel.json` — config de déploiement du frontend sur Vercel (rewrite `/api/*` vers le backend Render, pas de CORS côté navigateur) — voir ADR-006.

## Points d'entrée
API backend sous préfixe `/api/v1` — contrat complet et à jour dans `docs/contrat-api-phase1.md`, ne pas le dupliquer ici.

## Conventions
- Pas de Docker (ADR-001) : venv Python natif, PostgreSQL natif. Déploiement : Render (backend) + Vercel (frontend), pas de VPS — voir ADR-006 (révise le plan VPS initial de `docs/choix-technique-phase1.md`).
- Toute décision d'architecture structurante devient un ADR dans `docs/adr/`, jamais seulement actée en conversation.
- Un commit par artefact/endpoint livré (voir historique git) — pas de gros commits fourre-tout.

## Décisions d'architecture notables
- Monolithe modulaire, pas de microservices (ADR-001).
- Accès LLM (notation de documents, etc.) exclusivement via FreeLLM (service personnel, API compatible OpenAI), jamais l'API Anthropic en direct (ADR-002).
- Stockage de fichiers via LuluFiles, sauf le casier judiciaire qui reste local pour raisons légales — Art. 395 de la loi béninoise n° 2017-20 (ADR-003).
- Signature du contrat enseignant : tracé dessiné sur canvas (doigt/stylet), signature électronique simple, pas qualifiée — décision définitive de l'utilisateur (ADR-004).
- Notation/correction IA multi-appels (candidatures, devoirs) exécutée en arrière-plan (`BackgroundTasks`) pour ne jamais bloquer la requête sur la latence de FreeLLM ; génération de quiz (un seul appel) reste synchrone (ADR-005).
- Déploiement sur Render (backend) + Vercel (frontend), pas de VPS ; casier judiciaire sur disque persistant Render (une seule instance, pas d'autoscaling) ; CORS évité côté navigateur via un rewrite Vercel plutôt qu'ouvert (ADR-006).
- Design system frontend recentré sur une identité institutionnelle (État béninois) : palette fonctionnelle sobre, ombres diffuses, typographie Rubik/JetBrains Mono/Itim (wordmark uniquement), zéro emoji sur la plateforme (icônes `lucide-react` exclusivement), gamification cantonnée aux écrans élève (ADR-007).
- **[Proposé, non tranché]** Kkiapay ne supporte aucun versement programmable à un tiers (vérifié sur leur doc officielle) — bloque le séquestre micro-jobs (UC-18) tel que spécifié et rouvre le principe "LuluSchools n'héberge jamais les fonds elle-même" pour cette UC précise ; question posée à l'utilisateur (ADR-008).

## État d'avancement
Étapes 1-5 du pipeline validées pour la Phase 1. Étape 4 (backend) : tous les modules (UC-01 à UC-10) faits et testés (75 tests), 12 migrations appliquées en réel, mot de passe temporaire réellement appliqué côté serveur, notation/correction IA en arrière-plan (ADR-005). Étape 5 (validation de bout en bout) : scénario automatisé rejouant tout le parcours réel dans l'ordre — a révélé et corrigé un vrai bug (chemin du casier judiciaire mal interprété sous Windows). Étape 6 (frontend) : **les 5 rôles de la Phase 1 sont construits et testés en navigateur reel contre le backend reel**, sans mocks — Tuteur (inscription, consentement), Élève (cours, quiz IA, devoir corrigé par IA en arrière-plan, bulletin, réclamation), Enseignant (candidature, contrat signé par tracé canvas, cours/quiz/devoirs), A+ (validation d'inscriptions, classes, recrutement complet jusqu'au contrat, contestations, actes), A++ (création d'établissement, référentiels de coefficients). Ce test manuel a révélé et corrigé 3 vrais bugs backend et 1 bug frontend (détail dans `backend/PROJECT_MAP.md` et `frontend/PROJECT_MAP.md`). Prochaine étape : 7 (intégration — déjà de facto acquise vu qu'aucun mock n'a jamais été utilisé, reste à traiter les limites connues listées dans `frontend/PROJECT_MAP.md`) puis 8 (déploiement).

## Dernière synchronisation
2026-09-25 — Phases 2/3 : cas d'utilisation (UC-11 à UC-19) et diagrammes UML validés, contrat d'API écrit pour UC-11 à UC-17/UC-19 (`docs/contrat-api-phase2-3.md`). UC-18 (micro-jobs+séquestre) en attente : la doc Kkiapay confirme l'absence de versement programmable à un tiers, ce qui rouvre le principe "LuluSchools n'héberge jamais les fonds" pour cette UC (ADR-008, question posée à l'utilisateur). Par ailleurs, refonte du design system frontend vers une identité institutionnelle État béninois (ADR-007) — voir `frontend/PROJECT_MAP.md`.
