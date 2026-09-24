# Backend — Project Map (FastAPI)

## Identité
API LuluSchools : Python 3.13, FastAPI, SQLAlchemy 2.0 + Alembic, PostgreSQL, pas de Docker (venv + `requirements.txt`). Stack complète et justification : `../docs/choix-technique-phase1.md`. Contrat d'API à jour : `../docs/contrat-api-phase1.md`.

## Arborescence
- `app/core/` — config, connexion DB, sécurité (JWT, mots de passe, OTP), dépendances d'authentification FastAPI, client e-mail Brevo
- `app/system/` — endpoint de supervision (`/health`)
- `app/modules/identite/` — comptes utilisateurs (tuteur, auth, OTP)
- `app/modules/etablissements/` — établissements, classes, admins A+/A++
- `alembic/` — migrations (une par évolution de schéma, jamais réécrites une fois appliquées)
- `scripts/` — outils one-shot serveur (seed du tout premier compte A++)
- `tests/` — pytest, SQLite en mémoire (`StaticPool` pour partager la connexion entre threads), Brevo mocké via `FakeEmailClient` — aucun appel réseau réel dans la suite

## Fichiers clés

### app/core/
- `config.py` — `Settings` (pydantic-settings) ; lit `.env` à la **racine du dépôt**, chemin calculé depuis `__file__` (pas depuis le cwd — un premier bug l'avait fait chercher `backend/.env`, corrigé).
- `database.py` — engine SQLAlchemy, `SessionLocal`, `Base` (métadonnées partagées par tous les modules), dépendance `get_db`.
- `security.py` — hash Argon2 des mots de passe, génération/hash des OTP (HMAC-SHA256 salé, jamais stockés en clair), génération de mot de passe temporaire, création/décodage JWT (access + refresh, HS256).
- `deps.py` — `get_current_user` (décode le JWT, charge l'utilisateur), `require_roles(*roles)` (RBAC par dépendance FastAPI), `api_error()` (fabrique une `HTTPException` au format `{"error": {...}}` du contrat).
- `email.py` — `BrevoEmailClient.send_otp_email` / `.send_temporary_credentials_email`, appels HTTP directs à l'API Brevo. Injecté via `Depends(get_email_client)` pour rester substituable en test.

### app/modules/identite/
- `models.py` — `Utilisateur` (table de base commune à tous les rôles ; `login_id` = e-mail pour tuteur/enseignant/admin, matricule pour un élève), `Tuteur`, `OtpVerification`, enum `RoleUtilisateur`.
- `router.py` — `router` (`/auth/tuteurs`, `/auth/tuteurs/verify-otp` — UC-01) + `auth_router`/`me_router` (`/auth/login`, `/auth/refresh`, `/auth/change-password`, `/me`).
- `schemas.py` — schémas Pydantic stricts (`extra="forbid"`, anti mass-assignment), validateur de force de mot de passe partagé création/changement.

### app/modules/etablissements/
- `models.py` — `Etablissement`, `AdminEtablissement` (lien 1-1 vers `Utilisateur`), `Classe`, enums `TypeEtablissement`/`StatutEtablissement`/`PolitiqueDepassement`.
- `router.py` — `POST/GET /etablissements` (A++ seul pour créer, provisionne aussi le premier compte A+ avec mot de passe temporaire), `POST/GET /etablissements/{id}/classes` (A+, avec vérification stricte que l'admin administre bien CET établissement — anti-IDOR).

### alembic/versions/
- `0001_identite_initial.py` — utilisateurs, tuteurs, otp_verifications.
- `0002_identite_login_id.py` — ajoute `login_id`/`mot_de_passe_temporaire`, rend `email` optionnel.
- `0003_etablissements_classes.py` — etablissements, admins_etablissement, classes.
Toutes appliquées en réel sur la base configurée dans `.env` (upgrade **et** downgrade validés manuellement pour 0001).

### scripts/
- `seed_admin_ministeriel.py` — crée le tout premier compte A++ (aucune route API ne le fait, choix de sécurité assumé). À exécuter une fois au déploiement, directement sur le serveur.

## Modèle de données (résumé)
`Utilisateur` (1) → (0..1) `Tuteur`. `Utilisateur` (1) → (0..1) `AdminEtablissement` → (1) `Etablissement` (1) → (N) `Classe`. `Utilisateur` (1) → (N) `OtpVerification`.

## Conventions
- Un module métier = `models.py` + `schemas.py` + `router.py` sous `app/modules/<nom>/` ; pas de `service.py` séparé tant que la logique tient dans le router (à introduire si un router grossit trop).
- Toute réponse d'erreur passe par `api_error()` ou les gestionnaires globaux de `main.py` — jamais une `HTTPException` brute avec une simple chaîne de caractères.
- Schémas Pydantic toujours `extra="forbid"`.
- Compte provisionné (élève, admin établissement) = mot de passe temporaire envoyé par e-mail + `mot_de_passe_temporaire=True`.

## État d'avancement / zones instables
- Fait et testé (26 tests) : `/health`, module identité (UC-01 + auth JWT), module établissements/classes.
- En cours : inscriptions (UC-02/UC-03, avec auto-création du compte élève), recrutement/contrats (UC-04 à UC-05b), pédagogie/évaluations (UC-06 à UC-09), actes académiques (UC-10).
- **Fragile** : `mot_de_passe_temporaire` n'est pour l'instant qu'un indicateur renvoyé par `/auth/login` — rien ne bloque encore, côté serveur, les autres appels tant que le mot de passe temporaire n'a pas été changé.
- **Bloqué en attente d'un choix externe** : signature électronique qualifiée (UC-05) — aucun prestataire identifié, endpoint pas encore implémenté.

## Dernière synchronisation
2026-09-24 — après les modules identité et établissements/classes.
