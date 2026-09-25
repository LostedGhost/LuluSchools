# LuluSchools — Project Map

## Identité
Plateforme éducative nationale sous mandat ministériel (Bénin). Backend FastAPI/PostgreSQL — **toutes les phases connues à ce jour (UC-01 à UC-19) ont un backend complet, testé unitairement ET validé de bout en bout (120 tests)**. Frontend React (Vite/TS/Tailwind) — les 5 rôles de la Phase 1 sont fonctionnels et intégrés au backend réel ; le frontend Phase 2/3 n'existe pas encore. Développé avec la méthode spec-first `lucio-dev`. Cahier des charges Phase 1 : `docs/cas-utilisation-phase-1.md` ; Phases 2/3 (cas d'utilisation, UML, contrat d'API, backend et validation de bout en bout validés — étape 6 frontend restante) : `docs/cas-utilisation-phase-2-3.md`, `docs/diagrammes-uml-phase2-3.md`, `docs/contrat-api-phase2-3.md`. Décisions d'architecture : `docs/adr/`, avancement du pipeline : `SUIVI-PROJET.md`.

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
- Séquestre micro-jobs (UC-18) : Kkiapay n'offre pas de transfert ponctuel fiable vers un tiers (`setup_payout` existe mais configure une règle récurrente pour tout le compte, pas un virement par mission) — reversement au prestataire fait manuellement par un opérateur en V1, LuluSchools suit le séquestre comme un simple statut (ADR-008).
- Landing page : fond d'étoiles Three.js chargé à la demande + objets 3D flottants en CSS (jamais l'inverse — cf. raisonnement LuluFiles cité dans l'ADR) ; vitrine établissements réduite à un teaser sur la landing page, liste complète déportée sur un annuaire public dédié et paginé (`/etablissements`) ; photos d'établissement via LuluFiles, liens signés résolus à la demande par établissement, jamais en masse (ADR-009).

## État d'avancement

**Phase 1** — étapes 1-6 validées. Étape 4 (backend) : tous les modules (UC-01 à UC-10) faits et testés (75 tests), 12 migrations appliquées en réel, mot de passe temporaire réellement appliqué côté serveur, notation/correction IA en arrière-plan (ADR-005). Étape 5 (validation de bout en bout) : scénario automatisé rejouant tout le parcours réel dans l'ordre — a révélé et corrigé un vrai bug (chemin du casier judiciaire mal interprété sous Windows). Étape 6 (frontend) : **les 5 rôles de la Phase 1 sont construits et testés en navigateur reel contre le backend reel**, sans mocks — Tuteur (inscription, consentement), Élève (cours, quiz IA, devoir corrigé par IA en arrière-plan, bulletin, réclamation), Enseignant (candidature, contrat signé par tracé canvas, cours/quiz/devoirs), A+ (validation d'inscriptions, classes, recrutement complet jusqu'au contrat, contestations, actes), A++ (création d'établissement, référentiels de coefficients). Ce test manuel a révélé et corrigé 3 vrais bugs backend et 1 bug frontend (détail dans `backend/PROJECT_MAP.md` et `frontend/PROJECT_MAP.md`).

**Phase 2/3** — étapes 1 à 5 validées (voir `SUIVI-PROJET.md`) : cas d'utilisation, diagrammes UML, contrat d'API, **backend complet** pour les 9 UC (UC-11 à UC-19) — tickets transport/cantine, contrôle d'accès, billetterie, messagerie, assistant El Professor, cours vidéo, cours en direct, visites 3D/drone, micro-jobs+séquestre — et **validation de bout en bout** (`backend/tests/test_e2e_parcours_phase2_3.py`, même principe que `test_e2e_parcours_complet.py` : un seul établissement/classe/enseignant/élève/tuteur réutilisés à travers les 9 UC dans l'ordre réel, paiement Kkiapay réellement bouclé à chaque étape payante). 8 nouveaux modules, 8 migrations (0013-0020) appliquées en réel, 45 nouveaux tests (120 au total avec la Phase 1, aucune régression). Détail par module dans `backend/PROJECT_MAP.md`. Prochaine étape : 6 (frontend, non démarré pour ces 9 UC).

## Dernière synchronisation
2026-09-25 — Phase 2/3 : backend complet pour les 9 UC (UC-11 à UC-19) et validation de bout en bout (`test_e2e_parcours_phase2_3.py`), endpoint par endpoint avec tests immédiats comme en Phase 1. Webhook Kkiapay extrait de `actes/` vers un module `paiements/` partagé (Phase 1 + Phase 2/3, un seul webhook pour tout le compte). Deux corrections apportées au contrat en cours d'implémentation : arbitrage micro-jobs confié à l'A++ (pas "l'A+ de l'établissement du prestataire", qui n'existe pas pour un Tuteur prestataire), et ajout de `DELETE /messages/{id}` (masquage non destructeur, absent du premier jet). 120 tests passants. Par ailleurs, refonte du design system frontend vers une identité institutionnelle État béninois (ADR-007) — voir `frontend/PROJECT_MAP.md`. Landing page enrichie d'une scène 3D (étoiles Three.js + objets CSS flottants) et la vitrine établissements déportée sur un annuaire public dédié avec photos (ADR-009).
