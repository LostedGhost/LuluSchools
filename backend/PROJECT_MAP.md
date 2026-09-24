# Backend — Project Map (FastAPI)

## Identité
API LuluSchools : Python 3.13, FastAPI, SQLAlchemy 2.0 + Alembic, PostgreSQL, pas de Docker (venv + `requirements.txt`). Stack complète et justification : `../docs/choix-technique-phase1.md`. Contrat d'API à jour : `../docs/contrat-api-phase1.md`.

## Arborescence
- `app/core/` — config, connexion DB, sécurité (JWT, mots de passe, OTP), dépendances d'authentification FastAPI, client e-mail Brevo
- `app/system/` — endpoint de supervision (`/health`)
- `app/modules/identite/` — comptes utilisateurs (tuteur, auth, OTP)
- `app/modules/etablissements/` — établissements, classes, admins A+/A++
- `app/modules/inscriptions/` — inscriptions élève (consentement parental, validation, matricule, compte élève auto-créé)
- `app/modules/recrutement/` — postes, candidatures (notation IA + LuluFiles + casier judiciaire), contestations, contrats, reconduction
- `app/modules/pedagogie/` — cours, quiz (pas de banque de questions — voir zones instables)
- `app/modules/evaluations/` — devoirs, soumissions, référentiels de coefficients (UC-09), bulletins
- `app/modules/actes/` — catalogue d'actes académiques par établissement, demandes (réclamation ou acte payant)
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
- `files.py` — `LuluFilesClient.upload` / `.get_signed_link` (ADR-003), injecté via `Depends(get_files_client)`.
- `llm.py` — `FreeLLMClient.noter_document` : envoie une image en vision via l'API compatible OpenAI de FreeLLM, parse un score 0-100 depuis la réponse texte (ADR-002). Injecté via `Depends(get_llm_client)`.

### app/modules/identite/
- `models.py` — `Utilisateur` (table de base commune à tous les rôles ; `login_id` = e-mail pour tuteur/enseignant/admin, matricule pour un élève), `Tuteur`, `OtpVerification`, enum `RoleUtilisateur`.
- `router.py` — `router` (`/auth/tuteurs`, `/auth/tuteurs/verify-otp` — UC-01) + `auth_router`/`me_router` (`/auth/login`, `/auth/refresh`, `/auth/change-password`, `/me`).
- `schemas.py` — schémas Pydantic stricts (`extra="forbid"`, anti mass-assignment), validateur de force de mot de passe partagé création/changement.

### app/modules/etablissements/
- `models.py` — `Etablissement`, `AdminEtablissement` (lien 1-1 vers `Utilisateur`), `Classe`, enums `TypeEtablissement`/`StatutEtablissement`/`PolitiqueDepassement`.
- `router.py` — `POST/GET /etablissements` (A++ seul pour créer, provisionne aussi le premier compte A+ avec mot de passe temporaire), `POST/GET /etablissements/{id}/classes` (A+, avec vérification stricte que l'admin administre bien CET établissement — anti-IDOR).

### app/modules/inscriptions/
- `models.py` — `Eleve` (identité de l'élève, `utilisateur_id` nullable tant que non validée), `Inscription` (`statut` : en_attente_consentement_parental/soumise/validee/rejetee), enum `StatutInscription`.
- `router.py` — `POST /inscriptions` (Tuteur seul en Phase 1 — l'auto-inscription ≥16 ans sans tuteur n'est pas implémentée, nécessiterait un flux de compte dédié), branche d'âge Art. 446 (16 ans), `POST .../consentement-parental`, `POST .../valider` (A+, vérifie la capacité de la classe et génère matricule + compte élève), `POST .../rejeter`, `GET /inscriptions/{id}`.

### app/modules/recrutement/
- `models.py` — `Poste`, `CritereDocumentPoste` (coefficient + seuil par type de document), `Candidature`, `DocumentCandidature` (note IA), `VerificationCasierJudiciaire` (1-1, hors pipeline IA, fichier local — voir docstring, Art. 395), `Contestation`, `Contrat`, `PropositionReconduction` (modèle posé, endpoint pas encore écrit).
- `conversion.py` — `convertir_en_image()` : convertit la première page d'un PDF en PNG via PyMuPDF (FreeLLM n'accepte que des images en vision) ; passe les images telles quelles.
- `router.py` — `POST/GET /etablissements/{id}/postes`, `POST /postes/{id}/candidatures` (upload multipart, notation FreeLLM synchrone, casier judiciaire routé en stockage local), `GET /candidatures/{id}`, `POST /candidatures/{id}/contestation`, `POST /contestations/{id}/decision`, `POST /candidatures/{id}/contrat`, `POST /contrats/{id}/signer` (signature **simple**, pas encore qualifiée — voir zones instables).

### app/modules/pedagogie/
- `models.py` — `Cours`, `Quiz` (voir docstring : pas de banque de questions, non spécifiée par un UC validé), `TentativeQuiz`.
- `router.py` — `POST/GET /classes/{id}/cours`, `POST /cours/{id}/quiz`, `POST /quiz/{id}/tentatives`. Contient aussi `_verifier_enseignant_rattache` et `_verifier_eleve_inscrit`, réutilisées par `evaluations/router.py`.

### app/modules/evaluations/
- `models.py` — `Devoir`, `Soumission` (voir docstring : pas de ligne = 0 au bulletin), `ReferentielCoefficient` (gouvernance UC-09, pas encore branchée au calcul), `Bulletin`.
- `router.py` — `POST /classes/{id}/devoirs`, `POST /devoirs/{id}/soumissions` (rejette si en retard), `POST /soumissions/{id}/corriger`, gouvernance `/referentiels-coefficients*`, `GET /eleves/{id}/bulletins` (calcule et upsert), `POST /bulletins/{id}/valider-passage`.

### app/modules/actes/
- `models.py` — `TypeActeAcademique` (catalogue par établissement, voir UC-10 révisé), `DemandeActeAcademique`.
- `router.py` — `POST/GET /etablissements/{id}/types-actes`, `POST /demandes-actes`, `POST /demandes-actes/{id}/paiement/webhook` (stub, pas de vraie vérification Kkiapay), `POST /demandes-actes/{id}/traiter`.

### alembic/versions/
- `0001_identite_initial.py` — utilisateurs, tuteurs, otp_verifications.
- `0002_identite_login_id.py` — ajoute `login_id`/`mot_de_passe_temporaire`, rend `email` optionnel.
- `0003_etablissements_classes.py` — etablissements, admins_etablissement, classes.
- `0004_inscriptions.py` — eleves, inscriptions.
- `0005_enseignants.py` — enseignants.
- `0006_recrutement.py` — postes, criteres_document_poste, candidatures, documents_candidature, verifications_casier_judiciaire, contestations, contrats, propositions_reconduction.
- `0007_contrats_date_fin.py` — ajoute `date_fin` sur `contrats` (necessaire a la fenetre de reconduction).
- `0008_pedagogie_evaluations_actes.py` — cours, quiz, tentatives_quiz, devoirs, soumissions, referentiels_coefficients, bulletins, types_acte_academique, demandes_acte_academique.
Toutes appliquées en réel sur la base configurée dans `.env` (upgrade **et** downgrade validés manuellement pour 0001).

### scripts/
- `seed_admin_ministeriel.py` — crée le tout premier compte A++ (aucune route API ne le fait, choix de sécurité assumé). À exécuter une fois au déploiement, directement sur le serveur.

## Modèle de données (résumé)
`Utilisateur` (1) → (0..1) `Tuteur` | `Enseignant` | `AdminEtablissement`. `AdminEtablissement` (N) → (1) `Etablissement` (1) → (N) `Classe`. `Poste` (1) → (N) `CritereDocumentPoste`, (1) → (N) `Candidature` (1) → (N) `DocumentCandidature`, (1) → (0..1) `VerificationCasierJudiciaire`, (1) → (0..1) `Contestation`, (1) → (0..1) `Contrat`.

## Conventions
- Un module métier = `models.py` + `schemas.py` + `router.py` sous `app/modules/<nom>/` ; pas de `service.py` séparé tant que la logique tient dans le router (à introduire si un router grossit trop).
- Toute réponse d'erreur passe par `api_error()` ou les gestionnaires globaux de `main.py` — jamais une `HTTPException` brute avec une simple chaîne de caractères.
- Schémas Pydantic toujours `extra="forbid"`.
- Compte provisionné (élève, admin établissement) = mot de passe temporaire envoyé par e-mail + `mot_de_passe_temporaire=True`.

## État d'avancement / zones instables
Tous les modules de la Phase 1 (UC-01 à UC-10) ont un premier jet fait et testé (60 tests) : `/health`, identité, établissements/classes, inscriptions, recrutement/contrats (avec reconduction), pédagogie, évaluations, actes académiques.

- **Fragile** : `mot_de_passe_temporaire` n'est qu'un indicateur renvoyé par `/auth/login`, rien ne bloque encore côté serveur tant qu'il n'est pas changé.
- **Limitations assumées, documentées dans le contrat d'API** :
  - `POST /inscriptions` et `POST /demandes-actes` n'acceptent que le titulaire direct du compte (tuteur, élève) — pas de soumission pour compte d'un tiers.
  - Notation FreeLLM synchrone dans la requête (pas de file d'attente/tâche de fond).
  - Aucun endpoint de révision manuelle pour un document en `echec_notation` (candidature) — la donnée existe, l'action n'existe pas.
  - Contestation candidature comptée en jours calendaires plutôt qu'ouvrés.
  - Quiz : pas de banque de questions/réponses (non spécifiée) — le score est fourni par l'appelant.
  - Barème rigide (devoir) pas réellement auto-corrigé — pas de corrigé-type spécifié, la correction reste manuelle dans les deux cas.
  - Bulletin : moyenne simple sur les devoirs, **pas encore pondérée** par `ReferentielCoefficient` (la gouvernance UC-09 existe, le calcul ne s'en sert pas encore).
  - Webhook de paiement des actes académiques : forme posée, **aucune vérification de signature Kkiapay réelle** — à sécuriser avant production.
- **Bloqué en attente d'un choix externe** : signature électronique qualifiée (UC-05) — `POST /contrats/{id}/signer` implémente une signature simple en attendant un prestataire.

## Dernière synchronisation
2026-09-24 — après pédagogie, évaluations et actes académiques : premier jet complet de la Phase 1.
