# Backend — Project Map (FastAPI)

## Identité
API LuluSchools : Python 3.13, FastAPI, SQLAlchemy 2.0 + Alembic, PostgreSQL, pas de Docker (venv + `requirements.txt`). Stack complète et justification : `../docs/choix-technique-phase1.md`. Contrat d'API Phase 1 : `../docs/contrat-api-phase1.md` ; Phases 2/3 : `../docs/contrat-api-phase2-3.md`.

## Arborescence

**Phase 1**
- `app/core/` — config, connexion DB, sécurité (JWT, mots de passe, OTP), dépendances d'authentification FastAPI, client e-mail Brevo
- `app/system/` — endpoint de supervision (`/health`)
- `app/modules/identite/` — comptes utilisateurs (tuteur, auth, OTP)
- `app/modules/etablissements/` — établissements, classes, admins A+/A++
- `app/modules/inscriptions/` — inscriptions élève (consentement parental, validation, matricule, compte élève auto-créé)
- `app/modules/recrutement/` — postes, candidatures (notation IA + LuluFiles + casier judiciaire), contestations, contrats, reconduction
- `app/modules/pedagogie/` — cours (formats texte/PDF/audio/**vidéo**, UC-15), quiz généré par FreeLLM (QCM), **assistant El Professor** (UC-14)
- `app/modules/evaluations/` — devoirs, soumissions, référentiels de coefficients (UC-09), bulletins
- `app/modules/actes/` — catalogue d'actes académiques par établissement, demandes (réclamation ou acte payant)

**Phase 2/3** (voir `../docs/cas-utilisation-phase-2-3.md`)
- `app/modules/controle_acces/` — désignation du Contrôleur/Ticketeur, partagée par tickets/billetterie
- `app/modules/services_scolaires/` — tickets transport (UC-11) et cantine (UC-12)
- `app/modules/billetterie/` — événements et billets (UC-17)
- `app/modules/messagerie/` — DM + groupe de classe, signalements (UC-13)
- `app/modules/cours_direct/` — sessions live, consentement caméra (UC-16)
- `app/modules/visites_virtuelles/` — visites 3D/drone (UC-19)
- `app/modules/micro_jobs/` — offres, missions, séquestre (UC-18)
- `app/modules/paiements/` — webhook Kkiapay **partagé par tous les modules payants** (actes, tickets, billetterie, micro-jobs) — voir note ci-dessous

**Commun**
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
- `router.py` — `POST/GET /etablissements` (A++ seul pour créer, provisionne aussi le premier compte A+ avec mot de passe temporaire), `GET /etablissements/mon-etablissement` (point d'entrée du frontend A+ — sans lui, un A+ n'a aucun moyen de savoir quel établissement il administre, ce n'est pas exposé sur `MeOut` ; **attention à l'ordre des routes** : déclaré avant `GET /{etablissement_id}` sinon ce dernier capturerait `mon-etablissement` comme un id), `POST/GET /etablissements/{id}/classes` (A+, avec vérification stricte que l'admin administre bien CET établissement — anti-IDOR).

### app/modules/inscriptions/
- `models.py` — `Eleve` (identité de l'élève, `nationalite` enum NATIONALE/ETRANGERE, `utilisateur_id` nullable tant que non validée), `Inscription` (`statut` : en_attente_consentement_parental/soumise/validee/rejetee), enums `StatutInscription`, `Nationalite`.
- `router.py` — `POST /inscriptions` (Tuteur, ou Élève titulaire pour une réinscription sur son propre compte), branche d'âge Art. 446 (16 ans), `POST .../consentement-parental`, `POST .../valider` (A+, vérifie la capacité de la classe et génère le matricule via `_generer_matricule` + compte élève), `POST .../rejeter`, `GET /inscriptions/{id}`. Expose aussi `mon_espace_router` (sans préfixe `/inscriptions`, ajouté pour l'étape 6 frontend) : `GET /tuteurs/me/inscriptions` (les enfants du tuteur + statut, avec nom/prénom/matricule dénormalisés) et `GET /eleves/me` (profil + classe actuelle de l'élève courant, déduite de la dernière inscription validée).
- Matricule : format universitaire (UP) verrouillé `[nationalite:1][sequence:5][annee:2]` (8 car.) ; EP/ES proposé dans le même esprit `[cycle:1][nationalite:1][sequence:5][annee:2]` (9 car., cycle 7=EP/8=ES) — séquence = compteur national par `(cycle, nationalite, annee)`, calculé par pattern SQL `LIKE` à longueur fixe.
- `mon_espace_router` expose aussi `GET /etablissements/{id}/inscriptions-a-valider` (A+, ajouté pour l'étape 6 frontend — sans lui, l'admin n'a aucun moyen de découvrir les inscriptions `soumise` en attente).

### app/modules/recrutement/
- `models.py` — `Poste`, `CritereDocumentPoste` (coefficient + seuil par type de document), `Candidature`, `DocumentCandidature` (note IA), `VerificationCasierJudiciaire` (1-1, hors pipeline IA, fichier local — voir docstring, Art. 395), `Contestation`, `Contrat` (+ `date_fin`, + `signature_image_lulufiles_id`), `PropositionReconduction`. **Bugs corriges lors du test manuel en navigateur (etape 6)** :
  1. `DocumentCandidatureOut` n'exposait pas `id`, rendant l'ecran de revision manuelle (`POST /documents-candidature/{id}/noter-manuellement`) inutilisable en pratique (aucun moyen de connaitre l'id du document a noter depuis la reponse de l'API) — corrige.
  2. `ContratOut` n'exposait pas `etablissement_id`, rendant impossible pour le frontend enseignant de savoir dans quel etablissement publier un cours/devoir a partir de la liste de ses contrats — corrige.
  3. Aucune route ne permettait de lister les candidatures d'un poste (`GET /postes/{id}/candidatures`) : sans elle, un A+ n'avait litteralement aucun moyen d'utiliser `POST /candidatures/{id}/contrat` sans deja connaitre l'id de la candidature — ajoutee.
- `conversion.py` — `convertir_en_image()` : convertit la première page d'un PDF en PNG via PyMuPDF (FreeLLM n'accepte que des images en vision) ; passe les images telles quelles.
- `router.py` — `POST/GET /etablissements/{id}/postes` (liste ajoutée pour l'étape 6 frontend, découverte des postes ouverts), `GET /postes/{id}/candidatures` (toutes les candidatures d'un poste, réservé A+ — sans lui `POST .../contrat` est inutilisable en pratique), `POST /postes/{id}/candidatures` (upload multipart synchrone vers LuluFiles + conversion PDF->image locale, mais la notation FreeLLM part **en arrière-plan** via `BackgroundTasks` — voir `_noter_candidature_en_arriere_plan` et ADR-005 ; casier judiciaire routé en stockage local), `GET /candidatures/{id}`, `GET /mes-candidatures` / `GET /mes-contrats` (historique de l'enseignant courant), `GET /candidatures/en-attente-revision` + `POST /documents-candidature/{id}/noter-manuellement` (écran de révision manuelle, synchrone), `POST /candidatures/{id}/contestation`, `GET /etablissements/{id}/contestations-en-attente` + `POST /contestations/{id}/decision`, `POST /candidatures/{id}/contrat`, `POST /contrats/{id}/signer` (signature dessinée sur canvas, stockée via LuluFiles — décision finale, ADR-004), `POST /contrats/{id}/reconduction`.

### app/modules/pedagogie/
- `models.py` — `Cours`, `Quiz`, `QuestionQuiz` (généré par FreeLLM, QCM 4 choix), `TentativeQuiz` (stocke les `reponses` de l'élève en JSON + score calculé).
- `router.py` — `POST/GET /classes/{id}/cours`, `POST/GET /cours/{id}/quiz` (génération via `FreeLLMClient.generer_quiz` sur `cours.contenu_texte`, liste pour le frontend), `GET /quiz/{id}` (questions sans la bonne réponse), `POST /quiz/{id}/tentatives`, `GET /quiz/{id}/mes-tentatives` (historique de l'élève courant, ajoutés pour l'étape 6 frontend). Contient aussi `_verifier_enseignant_rattache` et `_verifier_eleve_inscrit`, réutilisées par `evaluations/router.py`.

### app/modules/evaluations/
- `models.py` — `Devoir` (+ `matiere`, + `QuestionDevoir` : énoncé, barème texte libre, points max), `Soumission` (+ `ReponseSoumission` : réponse élève + points obtenus + corrigée par IA ; `StatutSoumission` a 3 valeurs : `en_correction`/`corrigee`/`echec_correction`), `ReferentielCoefficient` (gouvernance UC-09, **branchée** au calcul du bulletin), `Bulletin`.
- `router.py` — `GET/POST /classes/{id}/devoirs` (liste ajoutée pour l'étape 6 frontend), `POST /devoirs/{id}/soumissions` (statut initial `en_correction`, correction via `FreeLLMClient.corriger_reponse` **en arrière-plan** par `BackgroundTasks` — voir `_corriger_soumission_en_arriere_plan` et ADR-005 ; `echec_correction` si FreeLLM indisponible), `GET /devoirs/{id}/ma-soumission` (l'élève courant retrouve sa propre soumission sans connaître son id), `GET /soumissions/{id}` (suivi de l'avancement, élève propriétaire/enseignant/A+), `GET /devoirs/{id}/soumissions-a-revoir` (écran de révision manuelle), `POST /soumissions/{id}/corriger` (manuel, synchrone, sert de filet de secours), gouvernance `/referentiels-coefficients*`, `GET /eleves/{id}/bulletins` (moyenne **pondérée** par coefficient, upsert), `POST /bulletins/{id}/valider-passage`.

### app/modules/actes/
- `models.py` — `TypeActeAcademique` (catalogue par établissement, voir UC-10 révisé), `DemandeActeAcademique` (+ `kkiapay_transaction_id`).
- `router.py` — `POST/GET /etablissements/{id}/types-actes`, `GET /mes-demandes-actes` (historique de l'élève ou de tous les enfants du tuteur), `GET /etablissements/{id}/demandes-actes` (écran A+, demandes a traiter), `POST /demandes-actes` (Élève ou Tuteur), `POST /demandes-actes/{id}/paiement/amorcer`, `POST /demandes-actes/{id}/traiter`.

### app/modules/paiements/ (Phase 2/3 — refactor du webhook Phase 1)
- `router.py` — `POST /paiements/webhook/kkiapay` : URL **unique pour tout le compte Kkiapay**, extraite hors d'`actes/` dès que les tickets/billetterie/micro-jobs en ont eu besoin (un seul webhook pour toute la plateforme, pas un par module). Vérifie `x-kkiapay-secret`, puis essaie de rattacher la transaction à chaque type de ressource payante en séquence (`_confirmer_demande_acte`, `_confirmer_ticket_transport`, `_confirmer_ticket_cantine`, `_confirmer_billet_evenement`, `_confirmer_mission_micro_job`) — une seule correspondra.
- `schemas.py` — `AmorcerPaiementRequest`/`KkiapayWebhookPayload` partagés, réexportés par `actes.schemas` pour compatibilité.

### app/modules/controle_acces/ (UC-11/UC-12/UC-17)
- `models.py` — `DesignationControleur` (établissement, utilisateur, `service` transport/cantine/evenement, `evenement_id` en string simple — pas une vraie FK, la table `evenements` n'existe pas encore à cette migration).
- `router.py` — `POST/GET /etablissements/{id}/controleurs`, `DELETE /controleurs/{id}` (A+ seul). Expose `verifier_admin_de_l_etablissement()` et `est_controleur_designe()`, réutilisées par `services_scolaires`, `billetterie`, `messagerie`, `visites_virtuelles`.

### app/modules/services_scolaires/ (UC-11, UC-12)
- `models.py` — `LigneTransport`/`TicketTransport`, `TypeRepasCantine`/`TicketCantine` (même `StatutTicket` partagé : acheté/validé/expiré/remboursé, `paiement_confirme` distinct du statut).
- `router.py` — achat par élève ou tuteur (`eleve_utilisateur_id` si tuteur), capacité vérifiée par date, validation réservée au Contrôleur désigné **et** au paiement confirmé, remboursement bloqué après la veille 18h ou une fois validé (Art. 354).

### app/modules/billetterie/ (UC-17)
- `models.py` — `Evenement` (+ `parrain_utilisateur_id`, délégation de gestion sans nouveau rôle RBAC), `BilletEvenement`.
- `router.py` — billet gratuit `paiement_confirme` d'office, annulation d'événement → remboursement intégral automatique de tous les billets (Art. 356), remboursement individuel bloqué à 48h de l'événement.

### app/modules/messagerie/ (UC-13)
- `models.py` — `Conversation` (DM ou groupe_classe — **la composition du groupe_classe n'est pas stockée, elle est calculée dynamiquement** à partir d'Inscription/Eleve/Contrat pour rester à jour sans hook cross-module), `ParticipantConversation` (DM seulement), `Message` (`masque_par` = suppression non destructrice), `SignalementMessage`.
- `router.py` — DM adulte↔élève interdit (403, décision utilisateur), groupe de classe créé automatiquement à la création de la `Classe` (hook dans `etablissements/router.py`), `DELETE /messages/{id}` masque sans supprimer (endpoint absent du premier jet du contrat, ajouté ici).

### app/modules/cours_direct/ (UC-16)
- `models.py` — `SessionLive`, `ConsentementCameraLive` (un par élève, distinct du consentement d'inscription), `ParticipationLive`.
- `router.py` — démarrage/fin réservés à l'enseignant organisateur, `camera_autorisee` dérivée de l'existence d'un consentement (jamais bloquant pour rejoindre), pas d'enregistrement, jeton de connexion placeholder (fournisseur SFU réel = choix technique différé).

### app/modules/visites_virtuelles/ (UC-19)
- `models.py` — `VisiteVirtuelle` (`attestation_autorisation` obligatoire, engagement déclaratif — drone/ANAC et droit à l'image hors portée du logiciel).
- `router.py` — publication réservée A+ (son établissement)/A++ (tous), lien externe uniquement (pas d'upload LuluFiles).

### app/modules/micro_jobs/ (UC-18)
- `models.py` — `OffreMicroJob`, `MissionMicroJob` (séquestre "Option A" — voir ADR-008 : le paiement transite par le compte Kkiapay unique de LuluSchools, le séquestre n'est qu'un statut suivi ici, pas un mécanisme Kkiapay natif), `ContestationMicroJob`.
- `router.py` — rôles autorisés (prestataire ou client) : Enseignant/Tuteur/A+/A++, **Élève structurellement exclu** (âge minimum légal de rémunération d'un mineur hors périmètre loi n° 2017-20, ADR-008). Validation tacite après 5 jours appliquée paresseusement (`_appliquer_validation_tacite`, pas de tâche planifiée). Arbitrage des contestations et reversement au prestataire réservés à l'**A++** (pas d'établissement résoluble pour une mission — un Tuteur prestataire n'en a aucun — correction du premier jet du contrat).

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
- `0013_designations_controleur.py` — table `designations_controleur` (UC-11/12/17).
- `0014_services_scolaires.py` — `lignes_transport`, `tickets_transport`, `types_repas_cantine`, `tickets_cantine` (UC-11/12). **Note** : l'enum Postgres `statutticket` est partagé par les deux tables de tickets dans la même migration — créé explicitement une seule fois avec `postgresql.ENUM(..., create_type=False)` sur les colonnes, sinon `op.create_table` retente de le créer pour la seconde table et échoue ("type already exists").
- `0015_billetterie.py` — `evenements`, `billets_evenement` (UC-17).
- `0016_messagerie.py` — `conversations`, `participants_conversation`, `messages`, `signalements_message` (UC-13).
- `0017_el_professor_et_video.py` — `sessions_el_professor`, `messages_el_professor` (UC-14) + valeur `VIDEO` ajoutée à l'enum `formatcours` (UC-15, même pattern `autocommit_block` que 0012).
- `0018_cours_direct.py` — `sessions_live`, `consentements_camera_live`, `participations_live` (UC-16).
- `0019_visites_virtuelles.py` — table `visites_virtuelles` (UC-19).
- `0020_micro_jobs.py` — `offres_micro_job`, `missions_micro_job`, `contestations_micro_job` (UC-18).
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
Tous les modules de la Phase 1 (UC-01 à UC-10) sont faits, testés unitairement ET validés de bout en bout (75 tests, dont `test_e2e_parcours_complet.py` qui rejoue tout le parcours réel) : `/health`, identité, établissements/classes, inscriptions, recrutement/contrats (avec reconduction et écran de révision manuelle), pédagogie (quiz généré par IA), évaluations (formulaires corrigés par IA, moyenne pondérée), actes académiques (avec webhook Kkiapay). Le mot de passe temporaire est désormais réellement appliqué côté serveur (`get_current_active_user` dans `app/core/deps.py` bloque toute requête avec 403 tant qu'il n'est pas changé, sauf `/me` et `/auth/change-password`).

**Bug réel trouvé et corrigé par le test de bout en bout** : `CASIER_JUDICIAIRE_STORAGE_PATH` avec un chemin absolu style Linux (`/var/lib/...`) était mal interprété par `pathlib` sous Windows — créait les fichiers sous la racine du lecteur courant (`D:\var\lib\...`) au lieu d'échouer ou d'utiliser le bon chemin. Corrigé en local (`.env` pointe désormais vers un chemin Windows explicite) ; `.env.example` documente le piège pour la prochaine personne qui développe sous Windows. Le chemin `/var/lib/...` reste correct pour un déploiement réel sur VPS Linux.

**Décisions définitives prises par l'utilisateur qui ferment d'anciens points ouverts :**
- Signature du contrat enseignant (UC-05) : tracé dessiné au doigt/stylet sur un canvas côté client, exporté en PNG, stocké via LuluFiles — signature électronique simple (Art. 284-285), pas qualifiée. Voir ADR-004. Ce n'est plus un point ouvert, c'est le choix retenu.
- Moyennes pondérées : `GET /eleves/{id}/bulletins` utilise désormais le coefficient (niveau, matière) du `ReferentielCoefficient` validé en vigueur (défaut 1.0 si aucun référentiel ne couvre la matière).
- Quiz (UC-07) : généré par FreeLLM à partir de `cours.contenu_texte` (QCM 4 choix). Devoirs (UC-08) : formulaires de questions, chacune avec son propre barème texte libre, corrigées automatiquement par FreeLLM (rigide = tout ou rien, flexible = crédit partiel).
- Écrans de révision manuelle : `GET /candidatures/en-attente-revision` + `POST /documents-candidature/{id}/noter-manuellement` (recrutement) et `GET /devoirs/{id}/soumissions-a-revoir` + `POST /soumissions/{id}/corriger` (évaluations), tous deux déclenchés quand FreeLLM échoue à noter/corriger (ADR-002).
- Inscriptions et demandes d'actes : le titulaire (l'élève, une fois son compte existant) peut désormais agir lui-même, en plus de son tuteur — plus seulement le tuteur.
- Webhook Kkiapay : corrigé pour respecter leur mécanique réelle (vérifiée sur leur documentation) — une URL **unique pour tout le compte** (`POST /paiements/webhook/kkiapay`), pas une par demande, avec vérification de l'en-tête `x-kkiapay-secret`. Le rattachement transaction ↔ demande se fait via `POST /demandes-actes/{id}/paiement/amorcer` (appelé côté client juste après avoir obtenu un `transactionId` du widget Kkiapay).

**Limitations assumées restantes, documentées dans le contrat d'API :**
- `POST /inscriptions` par un élève (titulaire) suppose qu'il a déjà un compte (réinscription) — la toute première inscription reste réservée au tuteur.

## Phase 2/3 (UC-11 à UC-19) — backend complet

Implémenté endpoint par endpoint après validation des cas d'utilisation (`../docs/cas-utilisation-phase-2-3.md`), des diagrammes UML (`../docs/diagrammes-uml-phase2-3.md`) et du contrat d'API (`../docs/contrat-api-phase2-3.md`). 8 migrations (0013 à 0020), toutes appliquées en réel. Décisions structurantes prises pendant l'implémentation (déléguées par l'utilisateur, voir [[feedback-legal-autonomy]]) :
- Groupe de classe de messagerie : composition calculée dynamiquement plutôt que stockée, pour ne pas avoir à maintenir des hooks dans `inscriptions`/`recrutement` à chaque inscription/contrat.
- Micro-jobs : reversement au prestataire manuel en V1 (`POST /missions-micro-job/{id}/reverser-prestataire`), après vérification approfondie que Kkiapay (SDK officiel, pas seulement le tableau de bord) n'offre pas de transfert ponctuel par mission — voir ADR-008.
- Micro-jobs : arbitrage des contestations et reversement réservés à l'A++ plutôt qu'à "l'A+ de l'établissement du prestataire" comme écrit dans le premier jet du contrat — un micro-job n'est rattaché à aucun établissement, et un Tuteur prestataire n'en a de toute façon aucun.
- Messagerie : `DELETE /messages/{id}` (masquage non destructeur) et signalement via écran de revue plutôt qu'un canal e-mail — deux détails absents du premier jet du contrat, ajoutés en cours d'implémentation sans changer les règles métier déjà validées.

## Dernière synchronisation
2026-09-25 — Phase 2/3 : backend complet pour les 9 UC (tickets transport/cantine, contrôle d'accès, billetterie, messagerie, El Professor, cours vidéo, cours en direct, visites 3D/drone, micro-jobs+séquestre), 8 migrations appliquées en réel. **119 tests passants** (75 Phase 1 + 44 Phase 2/3), aucune régression. Webhook Kkiapay extrait de `actes/` vers un module `paiements/` partagé.
