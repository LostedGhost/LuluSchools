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
- `app/modules/pedagogie/` — cours, quiz généré par FreeLLM (QCM)
- `app/modules/evaluations/` — devoirs, soumissions, référentiels de coefficients (UC-09), bulletins
- `app/modules/actes/` — catalogue d'actes académiques par établissement, demandes (réclamation ou acte payant)
- `alembic/` — migrations (une par évolution de schéma, jamais réécrites une fois appliquées)
- `scripts/` — outils one-shot serveur (seed du tout premier compte A++)
- `tests/` — pytest, SQLite en mémoire (`StaticPool` pour partager la connexion entre threads), tous les services externes mockés (Brevo/FreeLLM/LuluFiles) — aucun appel réseau réel dans la suite. `test_e2e_parcours_complet.py` rejoue tout le parcours UC-01 à UC-10 dans l'ordre réel, en plus des tests unitaires par module

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
- `models.py` — `Eleve` (identité de l'élève, `nationalite` enum NATIONALE/ETRANGERE, `utilisateur_id` nullable tant que non validée), `Inscription` (`statut` : en_attente_consentement_parental/soumise/validee/rejetee), enums `StatutInscription`, `Nationalite`.
- `router.py` — `POST /inscriptions` (Tuteur, ou Élève titulaire pour une réinscription sur son propre compte), branche d'âge Art. 446 (16 ans), `POST .../consentement-parental`, `POST .../valider` (A+, vérifie la capacité de la classe et génère le matricule via `_generer_matricule` + compte élève), `POST .../rejeter`, `GET /inscriptions/{id}`. Expose aussi `mon_espace_router` (sans préfixe `/inscriptions`, ajouté pour l'étape 6 frontend) : `GET /tuteurs/me/inscriptions` (les enfants du tuteur + statut, avec nom/prénom/matricule dénormalisés) et `GET /eleves/me` (profil + classe actuelle de l'élève courant, déduite de la dernière inscription validée).
- Matricule : format universitaire (UP) verrouillé `[nationalite:1][sequence:5][annee:2]` (8 car.) ; EP/ES proposé dans le même esprit `[cycle:1][nationalite:1][sequence:5][annee:2]` (9 car., cycle 7=EP/8=ES) — séquence = compteur national par `(cycle, nationalite, annee)`, calculé par pattern SQL `LIKE` à longueur fixe.
- `mon_espace_router` expose aussi `GET /etablissements/{id}/inscriptions-a-valider` (A+, ajouté pour l'étape 6 frontend — sans lui, l'admin n'a aucun moyen de découvrir les inscriptions `soumise` en attente).

### app/modules/recrutement/
- `models.py` — `Poste`, `CritereDocumentPoste` (coefficient + seuil par type de document), `Candidature`, `DocumentCandidature` (note IA), `VerificationCasierJudiciaire` (1-1, hors pipeline IA, fichier local — voir docstring, Art. 395), `Contestation`, `Contrat` (+ `date_fin`, + `signature_image_lulufiles_id`), `PropositionReconduction`. **Bug corrige lors du test manuel en navigateur** : `DocumentCandidatureOut` n'exposait pas `id`, rendant l'ecran de revision manuelle (`POST /documents-candidature/{id}/noter-manuellement`) inutilisable en pratique (aucun moyen de connaitre l'id du document a noter depuis la reponse de l'API) — corrige.
- `conversion.py` — `convertir_en_image()` : convertit la première page d'un PDF en PNG via PyMuPDF (FreeLLM n'accepte que des images en vision) ; passe les images telles quelles.
- `router.py` — `POST/GET /etablissements/{id}/postes` (liste ajoutée pour l'étape 6 frontend, découverte des postes ouverts), `POST /postes/{id}/candidatures` (upload multipart synchrone vers LuluFiles + conversion PDF->image locale, mais la notation FreeLLM part **en arrière-plan** via `BackgroundTasks` — voir `_noter_candidature_en_arriere_plan` et ADR-005 ; casier judiciaire routé en stockage local), `GET /candidatures/{id}`, `GET /mes-candidatures` / `GET /mes-contrats` (historique de l'enseignant courant), `GET /candidatures/en-attente-revision` + `POST /documents-candidature/{id}/noter-manuellement` (écran de révision manuelle, synchrone), `POST /candidatures/{id}/contestation`, `GET /etablissements/{id}/contestations-en-attente` + `POST /contestations/{id}/decision`, `POST /candidatures/{id}/contrat`, `POST /contrats/{id}/signer` (signature dessinée sur canvas, stockée via LuluFiles — décision finale, ADR-004), `POST /contrats/{id}/reconduction`.

### app/modules/pedagogie/
- `models.py` — `Cours`, `Quiz`, `QuestionQuiz` (généré par FreeLLM, QCM 4 choix), `TentativeQuiz` (stocke les `reponses` de l'élève en JSON + score calculé).
- `router.py` — `POST/GET /classes/{id}/cours`, `POST/GET /cours/{id}/quiz` (génération via `FreeLLMClient.generer_quiz` sur `cours.contenu_texte`, liste pour le frontend), `GET /quiz/{id}` (questions sans la bonne réponse), `POST /quiz/{id}/tentatives`, `GET /quiz/{id}/mes-tentatives` (historique de l'élève courant, ajoutés pour l'étape 6 frontend). Contient aussi `_verifier_enseignant_rattache` et `_verifier_eleve_inscrit`, réutilisées par `evaluations/router.py`.

### app/modules/evaluations/
- `models.py` — `Devoir` (+ `matiere`, + `QuestionDevoir` : énoncé, barème texte libre, points max), `Soumission` (+ `ReponseSoumission` : réponse élève + points obtenus + corrigée par IA ; `StatutSoumission` a 3 valeurs : `en_correction`/`corrigee`/`echec_correction`), `ReferentielCoefficient` (gouvernance UC-09, **branchée** au calcul du bulletin), `Bulletin`.
- `router.py` — `GET/POST /classes/{id}/devoirs` (liste ajoutée pour l'étape 6 frontend), `POST /devoirs/{id}/soumissions` (statut initial `en_correction`, correction via `FreeLLMClient.corriger_reponse` **en arrière-plan** par `BackgroundTasks` — voir `_corriger_soumission_en_arriere_plan` et ADR-005 ; `echec_correction` si FreeLLM indisponible), `GET /devoirs/{id}/ma-soumission` (l'élève courant retrouve sa propre soumission sans connaître son id), `GET /soumissions/{id}` (suivi de l'avancement, élève propriétaire/enseignant/A+), `GET /devoirs/{id}/soumissions-a-revoir` (écran de révision manuelle), `POST /soumissions/{id}/corriger` (manuel, synchrone, sert de filet de secours), gouvernance `/referentiels-coefficients*`, `GET /eleves/{id}/bulletins` (moyenne **pondérée** par coefficient, upsert), `POST /bulletins/{id}/valider-passage`.

### app/modules/actes/
- `models.py` — `TypeActeAcademique` (catalogue par établissement, voir UC-10 révisé), `DemandeActeAcademique` (+ `kkiapay_transaction_id`).
- `router.py` — `POST/GET /etablissements/{id}/types-actes`, `GET /mes-demandes-actes` (historique de l'élève ou de tous les enfants du tuteur), `GET /etablissements/{id}/demandes-actes` (écran A+, demandes a traiter), `POST /demandes-actes` (Élève ou Tuteur), `POST /demandes-actes/{id}/paiement/amorcer`, `POST /demandes-actes/{id}/traiter`. Expose aussi `paiements_router` : `POST /paiements/webhook/kkiapay` — URL **unique pour tout le compte** (pas par demande, correction d'une erreur de conception initiale), vérifie l'en-tête `x-kkiapay-secret` contre `settings.kkiapay_secret`.

### alembic/versions/
- `0001_identite_initial.py` — utilisateurs, tuteurs, otp_verifications.
- `0002_identite_login_id.py` — ajoute `login_id`/`mot_de_passe_temporaire`, rend `email` optionnel.
- `0003_etablissements_classes.py` — etablissements, admins_etablissement, classes.
- `0004_inscriptions.py` — eleves, inscriptions.
- `0005_enseignants.py` — enseignants.
- `0006_recrutement.py` — postes, criteres_document_poste, candidatures, documents_candidature, verifications_casier_judiciaire, contestations, contrats, propositions_reconduction.
- `0007_contrats_date_fin.py` — ajoute `date_fin` sur `contrats` (nécessaire à la fenêtre de reconduction).
- `0008_pedagogie_evaluations_actes.py` — cours, quiz, tentatives_quiz, devoirs, soumissions, referentiels_coefficients, bulletins, types_acte_academique, demandes_acte_academique.
- `0009_contrats_signature_image.py` — ajoute `signature_image_lulufiles_id` sur `contrats` (signature dessinée, remplace le nom tapé — ADR-004).
- `0010_formulaires_llm.py` — recrée `soumissions` en formulaire de réponses (plus de fichier joint), ajoute `questions_devoir`/`reponses_soumission`/`questions_quiz`, `matiere` sur `devoirs`, `reponses` sur `tentatives_quiz`, `kkiapay_transaction_id` sur `demandes_acte_academique`. **Note** : recrée la table `soumissions` plutôt que d'altérer l'enum Postgres en place — acceptable uniquement parce qu'aucune donnée réelle n'existait encore dans ces tables ; ne pas reproduire ce pattern une fois des données réelles présentes.
- `0011_eleves_nationalite.py` — ajoute `nationalite` (enum NATIONALE/ETRANGERE) sur `eleves`, nécessaire au nouveau format de matricule. **Note** : crée explicitement le type enum Postgres via `nationalite_enum.create(op.get_bind(), checkfirst=True)` avant le `ADD COLUMN` — `op.add_column` seul ne déclenche pas la création automatique du type (contrairement à une `Table` gérée par les métadonnées SQLAlchemy).
- `0012_soumissions_en_correction.py` — ajoute la valeur `EN_CORRECTION` à l'enum Postgres `statutsoumission` (voir ADR-005, correction IA passée en arrière-plan). **Note** : `ALTER TYPE ... ADD VALUE` doit sortir du bloc transactionnel d'Alembic (`op.get_context().autocommit_block()`) — pattern standard Postgres, sinon erreur "unsafe use of new value". Pas de downgrade réel possible (Postgres ne supporte pas `DROP VALUE` sur un enum).
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
Tous les modules de la Phase 1 (UC-01 à UC-10) sont faits, testés unitairement ET validés de bout en bout (68 tests, dont `test_e2e_parcours_complet.py` qui rejoue tout le parcours réel) : `/health`, identité, établissements/classes, inscriptions, recrutement/contrats (avec reconduction et écran de révision manuelle), pédagogie (quiz généré par IA), évaluations (formulaires corrigés par IA, moyenne pondérée), actes académiques (avec webhook Kkiapay). Le mot de passe temporaire est désormais réellement appliqué côté serveur (bloque l'écriture tant qu'il n'est pas changé).

**Bug réel trouvé et corrigé par le test de bout en bout** : `CASIER_JUDICIAIRE_STORAGE_PATH` avec un chemin absolu style Linux (`/var/lib/...`) était mal interprété par `pathlib` sous Windows — créait les fichiers sous la racine du lecteur courant (`D:\var\lib\...`) au lieu d'échouer ou d'utiliser le bon chemin. Corrigé en local (`.env` pointe désormais vers un chemin Windows explicite) ; `.env.example` documente le piège pour la prochaine personne qui développe sous Windows. Le chemin `/var/lib/...` reste correct pour un déploiement réel sur VPS Linux.

**Décisions définitives prises par l'utilisateur qui ferment d'anciens points ouverts :**
- Signature du contrat enseignant (UC-05) : tracé dessiné au doigt/stylet sur un canvas côté client, exporté en PNG, stocké via LuluFiles — signature électronique simple (Art. 284-285), pas qualifiée. Voir ADR-004. Ce n'est plus un point ouvert, c'est le choix retenu.
- Moyennes pondérées : `GET /eleves/{id}/bulletins` utilise désormais le coefficient (niveau, matière) du `ReferentielCoefficient` validé en vigueur (défaut 1.0 si aucun référentiel ne couvre la matière).
- Quiz (UC-07) : généré par FreeLLM à partir de `cours.contenu_texte` (QCM 4 choix). Devoirs (UC-08) : formulaires de questions, chacune avec son propre barème texte libre, corrigées automatiquement par FreeLLM (rigide = tout ou rien, flexible = crédit partiel).
- Écrans de révision manuelle : `GET /candidatures/en-attente-revision` + `POST /documents-candidature/{id}/noter-manuellement` (recrutement) et `GET /devoirs/{id}/soumissions-a-revoir` + `POST /soumissions/{id}/corriger` (évaluations), tous deux déclenchés quand FreeLLM échoue à noter/corriger (ADR-002).
- Inscriptions et demandes d'actes : le titulaire (l'élève, une fois son compte existant) peut désormais agir lui-même, en plus de son tuteur — plus seulement le tuteur.
- Webhook Kkiapay : corrigé pour respecter leur mécanique réelle (vérifiée sur leur documentation) — une URL **unique pour tout le compte** (`POST /paiements/webhook/kkiapay`), pas une par demande, avec vérification de l'en-tête `x-kkiapay-secret`. Le rattachement transaction ↔ demande se fait via `POST /demandes-actes/{id}/paiement/amorcer` (appelé côté client juste après avoir obtenu un `transactionId` du widget Kkiapay).

**Fragile** : `mot_de_passe_temporaire` n'est qu'un indicateur renvoyé par `/auth/login`, rien ne bloque encore côté serveur tant qu'il n'est pas changé.

**Limitations assumées restantes, documentées dans le contrat d'API :**
- Notation/correction FreeLLM synchrone dans la requête (pas de file d'attente/tâche de fond) — acceptable au volume Phase 1.
- Contestation candidature comptée en jours calendaires plutôt qu'ouvrés.
- `POST /inscriptions` par un élève (titulaire) suppose qu'il a déjà un compte (réinscription) — la toute première inscription reste réservée au tuteur.

## Dernière synchronisation
2026-09-25 — mot de passe temporaire réellement appliqué, délai de contestation en jours ouvrés, test de bout en bout (étape 5 du pipeline) écrit et passant, bug de chemin Windows trouvé et corrigé.
