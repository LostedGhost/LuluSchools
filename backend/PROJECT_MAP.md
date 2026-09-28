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

**Phase 4** (voir `../docs/cas-utilisation-phase-4-marketplace.md`)
- `app/modules/marketplace/` — annonces, photos, signalements, transactions et séquestre, contestations (UC-20/21/22)

**Phase 5** (voir `../docs/cahier-des-charges-refonte-admin-ministeriel.md` et `../docs/diagrammes-uml-phase-5-admin-ministeriel.md`)
- `app/modules/audit/` — `JournalAuditMinisteriel` (cible polymorphe) + `GET /admin/journal-audit` (UC-36/51/52) ; écrit exclusivement via `app/core/audit.py::journaliser_action_ministerielle` (point d'entrée unique, jamais construit à la main dans un router)

**Phase 2/3** (voir `../docs/cas-utilisation-phase-2-3.md`)
- `app/modules/controle_acces/` — désignation du Contrôleur/Ticketeur, partagée par tickets/billetterie
- `app/modules/services_scolaires/` — tickets transport (UC-11) et cantine (UC-12)
- `app/modules/billetterie/` — événements et billets (UC-17)
- `app/modules/messagerie/` — DM + groupe de classe, signalements (UC-13)
- `app/modules/cours_direct/` — sessions live, consentement caméra (UC-16)
- `app/modules/visites_virtuelles/` — visites 3D/drone (UC-19)
- `app/modules/micro_jobs/` — offres, missions, séquestre (UC-18)
- `app/modules/paiements/` — webhook Kkiapay **partagé par tous les modules payants** (actes, tickets, billetterie, micro-jobs) — voir note ci-dessous

**Phase 5 — Volet Professeur (UC-23 à UC-28)**
- `app/modules/vie_scolaire/` — absences, retards, appréciations, incidents (UC-23)
- `app/modules/evaluations/` — enrichi (UC-26) : nature formative/sommative, sujet/barème en document, soumission par copie image
- `app/modules/pedagogie/` — enrichi (UC-27) : El Professor côté enseignant (conseil éducatif/moral/professionnel) + garde-fou d'alerte
- `app/modules/pedagogie/el_professor_chat.py` (2026-09-27) — interface de conversation commune aux 4 personas : `POST /el-professor/{persona}/sessions/{id}/flux` (SSE, pièce jointe image/PDF), `PATCH`/`DELETE` d'une conversation, `GET/POST /el-professor/eleve/sessions` (aide générale sans cours), `POST /el-professor/synthese-vocale`. Réutilise les contrôles d'accès et `_detecter_signal_alerte` de `router.py` ; persistance après le flux via `get_session_factory`. Côté élève, seule la question déclenche l'alerte (origine `ELEVE`, exclue de la vue tuteur) et une consigne « détresse » est ajoutée avant l'appel.
- **Audit d'ergonomie (2026-09-28, `docs/audit-ergonomie-2026-09-28.md`)** :
  `app/core/messages_validation.py` (erreurs 422 en phrases françaises, branché dans
  `main.py`) ; `app/modules/administration/compteurs.py` (`GET /me/compteurs` : pastilles du
  menu par rôle) ; `app/modules/evaluations/periodes.py` (trimestres EP/ES, semestres UP ;
  `GET /classes/{id}/periodes`, bulletin limité aux devoirs de la période, erreur
  `periode_invalide`) ; tous les messages utilisateur accentués. Tests : `tests/test_periodes.py`,
  `test_compteurs_du_menu` ; helper `conftest.periode_courante` (les tests de bulletin ne
  dépendent plus de la date).
- **Simplification de l'administration (2026-09-28, `docs/simplification-administration.md`)** :
  `app/modules/administration/a_traiter.py` (`GET /administration/a-traiter` : toutes les files
  de l'A+ ou de l'A++, `POST /administration/remboursements/effectues`) ;
  `inscriptions/router.py::valider_inscription_interne` (validation unitaire, `valider-en-lot`,
  `rejeter-en-lot`, admission automatique via `Etablissement.admission_automatique`,
  `PATCH /etablissements/{id}/parametres`) ; `actes/generation.py` (attestation/relevé générés
  et livrés au paiement, `TypeActeAcademique.modele_document`) et `actes/analyse.py` (avis IA sur
  les réclamations) ; `recrutement/automatisation.py` (renotation planifiée, `recruter` en un clic,
  `reconduire-en-lot`) ; `etablissements/affectations_auto.py` (proposition/application) ;
  `core/moderation.py` (triage IA des signalements + `traiter-en-lot`) ; `core/litiges.py` (avis IA
  sur les litiges) ; `core/kkiapay.py` (remboursement automatique, `remboursement_effectue`) ;
  reversements groupés (`marketplace/transactions/reverser-en-lot`, `missions-micro-job/reverser-en-lot`).
  Migration `0019`. Tests : `tests/test_simplification_admin.py`.
- `app/core/documents.py` — lecture des PDF pour FreeLLM (qui ignore tout bloc non texte/image, voir `server/src/lib/content.ts` du fork) : texte extrait, ou 3 premières pages en PNG si scanné ; téléchargement borné. `pedagogie/router.py::texte_du_cours` fournit le texte d'un cours PDF à El Professor et à la génération de quiz (`Cours.texte_extrait`, extrait à la publication ou à la première demande).
- `app/core/llm.py` — consignes El Professor factorisées (`consigne_eleve_cours`, `consigne_eleve_general`, `consigne_enseignant`, `consigne_tuteur`, `consigne_famille`, `construire_messages_el_professor`), `diffuser_el_professor` (stream), `synthese_vocale` (voix Gemini, WAV allégé de moitié par `alleger_wav`). Consigne commune : Markdown + LaTeX, contexte béninois, jamais de numéro d'urgence cité.
- `app/modules/cours_direct/` — enrichi (UC-25) : tableau collaboratif, permissions de craie, chat de session, canal WebSocket temps réel

**Commun**
- `alembic/` — migrations (une par évolution de schéma, jamais réécrites une fois appliquées)
- `scripts/` — outils one-shot serveur (seed du tout premier compte A++) et `seed_mega.py` (voir section dédiée ci-dessous)
- `tests/` — pytest, SQLite en mémoire (`StaticPool` pour partager la connexion entre threads), tous les services externes mockés (Brevo/FreeLLM/LuluFiles) — aucun appel réseau réel dans la suite. `test_e2e_parcours_complet.py` rejoue tout le parcours UC-01 à UC-10 dans l'ordre réel (Phase 1), `test_e2e_parcours_phase2_3.py` fait de même pour UC-11 à UC-19 (Phase 2/3), en plus des tests unitaires par module

## Fichiers clés

### app/core/
- `config.py` — `Settings` (pydantic-settings) ; lit `.env` à la **racine du dépôt**, chemin calculé depuis `__file__` (pas depuis le cwd — un premier bug l'avait fait chercher `backend/.env`, corrigé).
- `database.py` — engine SQLAlchemy, `SessionLocal`, `Base` (métadonnées partagées par tous les modules), dépendance `get_db`.
- `security.py` — hash Argon2 des mots de passe, génération/hash des OTP (HMAC-SHA256 salé, jamais stockés en clair), génération de mot de passe temporaire, création/décodage JWT (access + refresh, HS256).
- `deps.py` — `get_current_user` (décode le JWT, charge l'utilisateur), `require_roles(*roles)` (RBAC par dépendance FastAPI), `api_error()` (fabrique une `HTTPException` au format `{"error": {...}}` du contrat). `get_current_active_user` bloque désormais aussi un compte `actif=false` (UC-35/50, Phase 5), en plus du mot de passe temporaire déjà géré.
- `audit.py` — `journaliser_action_ministerielle()` (Phase 5, UC-36/51) : point d'entrée unique pour écrire dans `modules/audit/models.py::JournalAuditMinisteriel` (n'écrit que si l'acteur est `ADMIN_MINISTERIEL`, silencieux sinon), appelé avant le `commit()` de l'action elle-même pour rester dans la même transaction.
- `email.py` — `BrevoEmailClient.send_otp_email` / `.send_temporary_credentials_email`, appels HTTP directs à l'API Brevo. Injecté via `Depends(get_email_client)` pour rester substituable en test. Envoie `htmlContent` (document HTML complet avec branding, pas un fragment `<p>` nu — un fragment sans `<!DOCTYPE html>/<html>/<body>` cassait le rendu chez certains clients mail) et `textContent` (secours texte seul). **Piège réel rencontré** : `BREVO_SENDER_EMAIL` doit être une adresse *vérifiée* dans le compte Brevo (Expéditeurs & IP) — avec le placeholder par défaut (`no-reply@luluschools.example`, domaine `.example` non routable), Brevo accepte la requête API (201/202, pas d'erreur visible côté appli) mais ne délivre jamais le mail.
- `files.py` — `LuluFilesClient.upload` / `.get_signed_link` (ADR-003), injecté via `Depends(get_files_client)`.
- `llm.py` — `FreeLLMClient.noter_document` : envoie une image en vision via l'API compatible OpenAI de FreeLLM, parse un score 0-100 depuis la réponse texte (ADR-002). Injecté via `Depends(get_llm_client)`.
- `rate_limit.py` — (audit 2026-09-27) limiteur en mémoire à fenêtre glissante (`verifier_limite`, `consommer`, `enregistrer_echec`), désactivé par `settings.rate_limit_enabled=False` dans la suite de tests (fixture `limitation_debit` pour le réactiver). Valable pour un seul worker.
- `reservation.py` — (audit 2026-09-27) `aujourdhui_benin()` (UTC+1) et `filtre_place_occupee()` : une place impayée ne compte dans la capacité que 30 min (tickets transport/cantine, billets).
- `files.py::lire_upload_borne()` — (audit 2026-09-27) lecture par blocs avec plafond de taille et liste blanche de types, à utiliser depuis un endpoint `def` pour **tout** téléversement.
- Sessions (audit 2026-09-27) : `security.marqueur_session()` embarque dans chaque refresh token l'empreinte de `Utilisateur.mot_de_passe_modifie_le` ; changer/réinitialiser le mot de passe révoque toutes les sessions. `deps.get_current_user` refuse désormais aussi un compte suspendu (`exiger_compte_actif`), `/me` compris. `config.Settings.verifier_configuration_production()` refuse de démarrer en production sans secrets valides.
- `crypto.py` — `chiffrer_bytes`/`dechiffrer_bytes` (Fernet) pour le casier judiciaire stocké en base (`recrutement/router.py`) ; la clé `CASIER_JUDICIAIRE_ENCRYPTION_KEY` est hashée (SHA-256) avant usage pour accepter n'importe quel format de secret (dont le base64 standard généré par `generateValue: true` de Render, pas garanti urlsafe comme l'exige Fernet).

### Audit de sécurité du 2026-09-27 (branche `audit/securite-approfondie`)
Détail complet : `docs/audit-securite-2026-09-27.md`. Points de repère pour reprendre le code :
- identite : `POST /auth/otp/renvoyer`, `POST /auth/mot-de-passe-oublie` (+ `/confirmer`), `OtpVerification.objet` (vérification e-mail vs réinitialisation), `change-password` renvoie une paire de tokens (`ChangePasswordOut`).
- recrutement : `GET /candidatures/{id}/casier-judiciaire` (+ `/document`, + `POST .../verdict`), réservés à l'A+ recruteur ; `purger_casiers_expires()` lancée par APScheduler en production (`main.py::lifespan`) ; `creer_contrat` exige un casier `CONFORME` ; `Candidature.rejetee_le` = départ du délai de contestation. **Ne jamais faire `.distinct()` sur une entité portant une colonne `JSON`** (erreur PostgreSQL) — utiliser une sous-requête `IN`.
- marketplace : `GET /etablissements/{id}/marketplace/transactions-a-reverser` (applique la confirmation tacite).
- Tests : `tests/test_securite_auth.py`, `tests/test_securite_acces.py`, `tests/test_securite_complements.py` ; `LULU_TEST_DATABASE_URL` rejoue toute la suite sur PostgreSQL (schéma créé une fois, tables vidées entre deux tests ; étape CI dédiée). Migrations `0016_durcissement_securite`, `0017_limitation_debit`.
- Seconde passe : webhook Kkiapay piloté par `partnerId` (`"<type>:<id>"`, voir `paiements/router.py::_MODELES_PAR_TYPE`, le frontend l'envoie via `KkiapayButton.typeRessource`) ; limitation de débit en base (`identite.models.TentativeLimitee`, signatures `rate_limit.*(db, ...)`) ; messages paginés (`limite`, `avant`) ; inscription/OTP sans énumération ; DM élève↔élève limité au même établissement ; contrôleur restreint à `controle_acces.router._est_designable`.

### app/modules/identite/
- `models.py` — `Utilisateur` (table de base commune à tous les rôles ; `login_id` = e-mail pour tuteur/enseignant/admin, matricule pour un élève), `Tuteur`, `OtpVerification`, enum `RoleUtilisateur`.
- `router.py` — `router` (`/auth/tuteurs`, `/auth/tuteurs/verify-otp` — UC-01) + `auth_router`/`me_router` (`/auth/login`, `/auth/refresh`, `/auth/change-password`, `GET /me`, `PATCH /me` — numéro Mobile Money, seul champ modifiable par l'utilisateur, requis pour les reversements marketplace/micro-jobs).
- `schemas.py` — schémas Pydantic stricts (`extra="forbid"`, anti mass-assignment), validateur de force de mot de passe partagé création/changement.

### app/modules/etablissements/
- `models.py` — `Etablissement`, `AdminEtablissement` (lien 1-1 vers `Utilisateur`), `Classe`, `AffectationEnseignant` (migration `0005`, lien enseignant↔classe précise — voir la synchro du 2026-09-26 ci-dessous, `Contrat` seul ne suffisait plus), `EtablissementPhoto` (ADR-009, migration `0021` — ne stocke que `lulufiles_file_id` + `ordre`, jamais d'URL brute), enums `TypeEtablissement`/`StatutEtablissement`/`PolitiqueDepassement`.
- `router.py` — `POST/GET /etablissements` (A++ seul pour créer, provisionne aussi le premier compte A+ avec mot de passe temporaire), `GET /etablissements/mon-etablissement` (point d'entrée du frontend A+ — sans lui, un A+ n'a aucun moyen de savoir quel établissement il administre, ce n'est pas exposé sur `MeOut` ; **attention à l'ordre des routes** : déclaré avant `GET /{etablissement_id}` sinon ce dernier capturerait `mon-etablissement` comme un id), `POST/GET /etablissements/{id}/classes` (A+, avec vérification stricte que l'admin administre bien CET établissement — anti-IDOR).
- **Endpoints publics (sans authentification)** — avec `GET /health` (`app/system/router.py`), les seuls de tout le backend ; tous déclarés avant `GET /{etablissement_id}` pour l'ordre des routes (ADR-009) :
  - `GET /etablissements/vitrine-publique` — teaser léger pour la landing page (3 établissements en avant, quelques postes ouverts, totaux globaux). N'expose que des champs non sensibles (`EtablissementVitrineOut`/`PosteVitrineOut`/`VitrinePubliqueOut`, jamais `code_etablissement` ni d'email d'admin). Importe `Poste`/`StatutPoste` depuis `modules/recrutement/models.py` (couplage en lecture seule, cohérent avec l'import déjà existant de `modules/messagerie/models`).
  - `GET /etablissements/annuaire-public?type=&q=&limit=&offset=` — annuaire complet paginé, pour la page dédiée `/etablissements` du frontend (jamais la landing page — la plateforme a vocation nationale). **`limit` plafonné cote serveur a 60 quel que soit ce qui est demandé**, ne jamais faire confiance a un client pour borner sa propre requête.
  - `GET /etablissements/{id}/photos-publiques` — résout les liens signés LuluFiles à la demande, **appelé uniquement pour un établissement précis** (jamais en boucle sur toute une page d'annuaire, pour ne pas multiplier les appels vers LuluFiles — voir le risque de quota déjà signalé sur ce service). `POST`/`DELETE /etablissements/{id}/photos` (A+ de l'établissement ou A++ sans restriction, via `verifier_portee_etablissement` — voir `core/deps.py` et la synchro du 2026-09-26, max 8 photos) gèrent l'upload/suppression réelle.
- `classes_router` (sans préfixe, monté séparément dans `main.py`) : `POST/GET /classes/{id}/affectations` et `DELETE /affectations/{id}` (A+/A++, gère `AffectationEnseignant` — exige un `Contrat` SIGNE préalable avec l'établissement de la classe), `GET /mes-classes-affectees` (Enseignant — ses classes assignées, remplace la découverte via un `Contrat` établissement-large).

### app/modules/inscriptions/
- `models.py` — `Eleve` (identité de l'élève, `nationalite` enum NATIONALE/ETRANGERE, `utilisateur_id` nullable tant que non validée), `Inscription` (`statut` : en_attente_consentement_parental/soumise/validee/rejetee), enums `StatutInscription`, `Nationalite`.
- `router.py` — `POST /inscriptions` (Tuteur, ou Élève titulaire pour une réinscription sur son propre compte), branche d'âge Art. 446 (16 ans), `POST .../consentement-parental`, `POST .../valider` (A+, vérifie la capacité de la classe et génère le matricule via `_generer_matricule` + compte élève), `POST .../rejeter`, `GET /inscriptions/{id}`. Expose aussi `mon_espace_router` (sans préfixe `/inscriptions`, ajouté pour l'étape 6 frontend) : `GET /tuteurs/me/inscriptions` (les enfants du tuteur + statut, avec nom/prénom/matricule dénormalisés) et `GET /eleves/me` (profil + classe actuelle de l'élève courant, déduite de la dernière inscription validée).
- Matricule : format universitaire (UP) verrouillé `[nationalite:1][sequence:5][annee:2]` (8 car.) ; EP/ES proposé dans le même esprit `[cycle:1][nationalite:1][sequence:5][annee:2]` (9 car., cycle 7=EP/8=ES) — séquence = compteur national par `(cycle, nationalite, annee)`, calculé par pattern SQL `LIKE` à longueur fixe.
- `mon_espace_router` expose aussi `GET /etablissements/{id}/inscriptions-a-valider` (A+, ajouté pour l'étape 6 frontend — sans lui, l'admin n'a aucun moyen de découvrir les inscriptions `soumise` en attente).

### app/modules/recrutement/
- `models.py` — `Poste`, `CritereDocumentPoste` (coefficient + seuil par type de document), `Candidature`, `DocumentCandidature` (note IA), `VerificationCasierJudiciaire` (1-1, hors pipeline IA, contenu chiffre Fernet stocke en base `contenu_chiffre` — jamais sur LuluFiles, voir docstring + `app/core/crypto.py`, Art. 395 ; remplace l'ancien `chemin_fichier_local` sur disque, incompatible avec le plan Render gratuit sans disque persistant), `Contestation`, `Contrat` (+ `date_fin`, + `signature_image_lulufiles_id`), `PropositionReconduction`. **Bugs corriges lors du test manuel en navigateur (etape 6)** :
  1. `DocumentCandidatureOut` n'exposait pas `id`, rendant l'ecran de revision manuelle (`POST /documents-candidature/{id}/noter-manuellement`) inutilisable en pratique (aucun moyen de connaitre l'id du document a noter depuis la reponse de l'API) — corrige.
  2. `ContratOut` n'exposait pas `etablissement_id`, rendant impossible pour le frontend enseignant de savoir dans quel etablissement publier un cours/devoir a partir de la liste de ses contrats — corrige.
  3. Aucune route ne permettait de lister les candidatures d'un poste (`GET /postes/{id}/candidatures`) : sans elle, un A+ n'avait litteralement aucun moyen d'utiliser `POST /candidatures/{id}/contrat` sans deja connaitre l'id de la candidature — ajoutee.
  4. **Trouve en auditant le frontend Phase 1 (2026-09-25)** : `DocumentCandidatureOut` n'exposait pas `lulufiles_file_id` — ni le candidat ni l'A+ ne pouvaient jamais consulter le document lui-meme (seule la note IA etait visible), rendant l'ecran de revision manuelle inutilisable pour ce qu'il est cense faire. `GET /documents-candidature/{id}/lien` ajoute. Meme constat pour la signature de contrat : `GET /contrats/{id}/lien-signature` ajoute.
  5. **Meme audit** : `CandidatureOut` n'exposait que des identifiants — une candidature etait litteralement anonyme pour l'A+ censé décider d'un recrutement réel. `enseignant_nom`/`enseignant_prenom` ajoutés (propriété Python sur `Candidature`, relation `enseignant` vers `identite.Enseignant`/`Utilisateur` — pas de reconstruction manuelle par endpoint, cohérent avec le fait que `CandidatureOut` est renvoyé par ~6 endpoints différents).
- `conversion.py` — `convertir_en_image()` : convertit la première page d'un PDF en PNG via PyMuPDF (FreeLLM n'accepte que des images en vision) ; passe les images telles quelles.
- `router.py` — `POST/GET /etablissements/{id}/postes` (liste ajoutée pour l'étape 6 frontend, découverte des postes ouverts), `GET /postes/{id}/candidatures` (toutes les candidatures d'un poste, réservé A+ — sans lui `POST .../contrat` est inutilisable en pratique), `POST /postes/{id}/candidatures` (upload multipart synchrone vers LuluFiles + conversion PDF->image locale, mais la notation FreeLLM part **en arrière-plan** via `BackgroundTasks` — voir `_noter_candidature_en_arriere_plan` et ADR-005 ; casier judiciaire routé en stockage local), `GET /candidatures/{id}`, `GET /mes-candidatures` / `GET /mes-contrats` (historique de l'enseignant courant), `GET /candidatures/en-attente-revision` + `POST /documents-candidature/{id}/noter-manuellement` (écran de révision manuelle, synchrone), `POST /candidatures/{id}/contestation`, `GET /etablissements/{id}/contestations-en-attente` + `POST /contestations/{id}/decision`, `POST /candidatures/{id}/contrat`, `POST /contrats/{id}/signer` (signature dessinée sur canvas, stockée via LuluFiles — décision finale, ADR-004), `POST /contrats/{id}/reconduction`.

### app/modules/pedagogie/
- `models.py` — `Cours`, `Quiz`, `QuestionQuiz` (généré par FreeLLM, QCM 4 choix), `TentativeQuiz` (stocke les `reponses` de l'élève en JSON + score calculé).
- `router.py` — `POST/GET /classes/{id}/cours`, `POST/GET /cours/{id}/quiz` (génération via `FreeLLMClient.generer_quiz` sur `cours.contenu_texte`, liste pour le frontend), `GET /quiz/{id}` (questions sans la bonne réponse), `POST /quiz/{id}/tentatives`, `GET /quiz/{id}/mes-tentatives` (historique de l'élève courant, ajoutés pour l'étape 6 frontend). Contient aussi `_verifier_enseignant_rattache` et `_verifier_eleve_inscrit`, réutilisées par `evaluations/router.py`.
- **Bug réel trouvé en auditant le frontend Phase 1 (2026-09-25)** : `CoursOut` n'exposait jamais `contenu_texte` — un cours de format `texte` (UC-06) était donc littéralement illisible par l'élève depuis le tout début (le champ n'existait que pour la génération de quiz, en interne). Et aucune route ne transformait jamais un `lulufiles_file_id` (pdf/audio/vidéo) en lien consultable — `LuluFilesClient.get_signed_link()` existait mais n'était appelé nulle part dans tout le backend. Corrigé : `contenu_texte` ajouté à `CoursOut`, `GET /cours/{id}/lien-fichier` ajouté (même RBAC que la liste des cours).

### app/modules/evaluations/
- `models.py` — `Devoir` (+ `matiere`, + `QuestionDevoir` : énoncé, barème texte libre, points max), `Soumission` (+ `ReponseSoumission` : réponse élève + points obtenus + corrigée par IA ; `StatutSoumission` a 3 valeurs : `en_correction`/`corrigee`/`echec_correction`), `ReferentielCoefficient` (gouvernance UC-09, **branchée** au calcul du bulletin), `Bulletin`.
- `router.py` — `GET/POST /classes/{id}/devoirs` (liste ajoutée pour l'étape 6 frontend), `POST /devoirs/{id}/soumissions` (statut initial `en_correction`, correction via `FreeLLMClient.corriger_reponse` **en arrière-plan** par `BackgroundTasks` — voir `_corriger_soumission_en_arriere_plan` et ADR-005 ; `echec_correction` si FreeLLM indisponible), `GET /devoirs/{id}/ma-soumission` (l'élève courant retrouve sa propre soumission sans connaître son id), `GET /soumissions/{id}` (suivi de l'avancement, élève propriétaire/enseignant/A+), `GET /devoirs/{id}/soumissions-a-revoir` (écran de révision manuelle), `GET /devoirs/{id}/questions-bareme` (**bug réel corrigé, audit frontend 2026-09-25** : l'écran de révision manuelle affichait un champ de points sans jamais montrer le barème que l'enseignant avait lui-même rédigé — endpoint dédié réservé au propriétaire, jamais fusionné dans `DevoirOut` qui reste lisible par l'Élève avant sa réponse), `POST /soumissions/{id}/corriger` (manuel, synchrone, sert de filet de secours), gouvernance `/referentiels-coefficients*`, `GET /eleves/{id}/bulletins` (moyenne **pondérée** par coefficient, upsert), `POST /bulletins/{id}/valider-passage`.

### app/modules/actes/
- `models.py` — `TypeActeAcademique` (catalogue par établissement, voir UC-10 révisé), `DemandeActeAcademique` (+ `kkiapay_transaction_id`).
- `router.py` — `POST/GET /etablissements/{id}/types-actes`, `GET /mes-demandes-actes` (historique de l'élève ou de tous les enfants du tuteur), `GET /etablissements/{id}/demandes-actes` (écran A+, demandes a traiter), `POST /demandes-actes` (Élève ou Tuteur), `POST /demandes-actes/{id}/paiement/amorcer`, `POST /demandes-actes/{id}/traiter`.
- **Écart réel repéré mais non corrigé (2026-09-25)**, documenté plutôt que silencieusement laissé de côté : UC-10 prévoit que le demandeur « fournit les pièces justificatives requises (upload via LuluFiles) », mais `POST /demandes-actes` n'a jamais accepté ni stocké aucun fichier — `pieces_requises` sur `TypeActeAcademique` reste une simple liste en texte libre affichée à l'utilisateur, sans upload réel en face. Contrairement aux deux bugs ci-dessus (cours illisible, document de candidature invisible), corriger celui-ci suppose de changer la forme de la requête (JSON → multipart) d'un endpoint déjà livré et intégré au frontend — une bascule plus risquée qu'un ajout pur, mise de côté pour rester concentré sur le frontend Phase 2/3 demandé. À reprendre si les actes payants/pièces jointes deviennent un vrai point de friction.

### app/modules/paiements/ (Phase 2/3 — refactor du webhook Phase 1)
- `router.py` — `POST /paiements/webhook/kkiapay` : URL **unique pour tout le compte Kkiapay**, extraite hors d'`actes/` dès que les tickets/billetterie/micro-jobs en ont eu besoin (un seul webhook pour toute la plateforme, pas un par module). Vérifie `x-kkiapay-secret`, puis essaie de rattacher la transaction à chaque type de ressource payante en séquence (`_confirmer_demande_acte`, `_confirmer_ticket_transport`, `_confirmer_ticket_cantine`, `_confirmer_billet_evenement`, `_confirmer_mission_micro_job`) — une seule correspondra.
- `schemas.py` — `AmorcerPaiementRequest`/`KkiapayWebhookPayload` partagés, réexportés par `actes.schemas` pour compatibilité.

### app/modules/controle_acces/ (UC-11/UC-12/UC-17)
- `models.py` — `DesignationControleur` (établissement, utilisateur, `service` transport/cantine/evenement, `evenement_id` en string simple — pas une vraie FK, la table `evenements` n'existe pas encore à cette migration).
- `router.py` — `POST/GET /etablissements/{id}/controleurs`, `DELETE /controleurs/{id}` (A+ de l'établissement ou A++). Expose `verifier_admin_de_l_etablissement()` (délègue désormais à `core/deps.py::verifier_portee_etablissement`, seule source de vérité — voir la synchro du 2026-09-26) et `est_controleur_designe()`, réutilisées par `services_scolaires`, `billetterie`, `messagerie`, `visites_virtuelles`.

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

### app/modules/marketplace/ (UC-20/21/22, Phase 4)
- `models.py` — `AnnonceMarketplace` (`etablissement_id` denormalisé, fixé à la publication à partir de l'établissement du vendeur — pas recalculé dynamiquement comme le groupe de classe de messagerie), `PhotoAnnonceMarketplace`, `SignalementAnnonceMarketplace`, `TransactionMarketplace` (séquestre "Option A", même modèle qu'UC-18/ADR-008 ; `annonce_id` **pas** unique — une transaction annulée/remboursée ne doit jamais bloquer une réservation ultérieure de la même annonce), `ContestationMarketplace`.
- `router.py` — réservé aux élèves ≥16 ans (réutilise `AGE_MAJORITE_NUMERIQUE`/`_age_a` d'`inscriptions/router.py`, pas dupliqué) inscrits et validés dans l'établissement concerné (`_verifier_eleve_de_l_etablissement`, calcul dynamique via `Eleve`/`Inscription VALIDEE`/`Classe`, même esprit que `messagerie/router.py`). Upload multipart de 1..n photos à la création (`Form`+`File`, même pattern que `recrutement.postuler`), au moins une obligatoire (`422` sinon). Arbitrage des contestations et reversement au vendeur réservés à l'**A+ de l'établissement** (pas l'A++ comme les micro-jobs, UC-18) — non ambigu ici car vendeur et acheteur sont toujours du même établissement. Retrait d'une annonce par l'A+ rembourse/annule automatiquement la transaction en cours si l'annonce était `réservée`. Validation tacite de la réception après 5 jours appliquée paresseusement (`_appliquer_confirmation_tacite`, même technique que UC-18), pas de tâche planifiée.
- Webhook Kkiapay (`app/modules/paiements/router.py`) étendu avec `_confirmer_transaction_marketplace`, même séquence d'essais que les autres ressources payantes.

### alembic/versions/
**Squashées en une seule migration le 2026-09-26** : `0001_schema_initial.py`, générée par `alembic revision --autogenerate` contre une base vide (donc directement depuis l'état actuel des modèles SQLAlchemy, pas depuis l'historique des 22 migrations précédentes, supprimées). Déclenché par un vrai bug de déploiement Render (l'ancienne `0010_formulaires_llm.py` faisait `DROP TYPE statutsoumission` puis recréait aussitôt une table l'utilisant, ce qui échouait avec `UndefinedObject: type "statutsoumission" does not exist`) — voir le docstring de `0001_schema_initial.py` pour le détail complet, et la section `seed_mega.py` ci-dessous pour l'impact sur `alembic_version`.

**Conséquence pour le dev local** : toute base Postgres locale ayant déjà l'ancien historique de migrations (`alembic_version` pointant vers `0022_...`) doit être recréée (`DROP DATABASE` + `CREATE DATABASE` + `alembic upgrade head`) plutôt que mise à jour en place — l'ancienne revision n'existe plus dans le code.

**Convention qui reprend à partir d'ici** : une migration par évolution de schéma, jamais réécrite une fois appliquée en production réelle (l'exception ci-dessus ne vaut que pour du pré-pilote sans données réelles).

### scripts/
- `seed_admin_ministeriel.py` — crée le tout premier compte A++ (aucune route API ne le fait, choix de sécurité assumé). À exécuter une fois au déploiement, directement sur le serveur.
- `seed_mega.py` + `seed_donnees/` — seed « grandeur nature » cohérent avec le workflow réel (UAC toujours présente), `verifier_seed.py` (39 règles métier), `seed_render.bat` (seed de la base en ligne). Voir section dédiée ci-dessous.

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

**Étape 5 (validation de bout en bout) close** : `tests/test_e2e_parcours_phase2_3.py` — même principe que `test_e2e_parcours_complet.py` (Phase 1), un seul jeu d'objets réutilisé à travers tous les modules plutôt que des fixtures isolées par test. Ordre rejoué : messagerie (groupe de classe auto-créé, DM tuteur→enfant, DM adulte→élève refusé, signalement traité) → El Professor + cours vidéo → cours en direct (consentement caméra, démarrage, participation, fin) → tickets transport et cantine (même enseignant cumulant les deux désignations de Contrôleur) → billetterie → visite virtuelle 3D → micro-job (offre → paiement → déclaration → validation → reversement A++). N'a pas révélé de bug d'intégration (contrairement à la Phase 1, qui en avait révélé plusieurs) — les modules Phase 2/3 réutilisent systématiquement les mêmes helpers RBAC (`verifier_admin_de_l_etablissement`, `est_controleur_designe`) que les tests unitaires exerçaient déjà.

## Seed grandeur nature (`scripts/seed_mega.py` + paquet `scripts/seed_donnees/`)

**Réécrit le 2026-09-27** : l'ancien seed (antérieur à l'audit) produisait des données
incohérentes avec les règles des routeurs (plusieurs contrats par poste, contrat sans casier
conforme, un seul enseignant pour 15 classes, moyennes de bulletin inventées sur 20 au lieu
d'être calculées sur 100, identifiants de fichiers fictifs donnant des liens cassés,
sessions « en cours » figées, tickets validés dans le futur...). Le nouveau seed rejoue le
workflow réel de chaque entité ; chaque module du paquet documente les règles qu'il suit :

- `contexte.py` — configuration (`--scale`), horloge (tout est daté par rapport au moment du
  seed : rentrée mi-septembre, activité entre la rentrée et maintenant), insertion **groupée
  par table dans l'ordre des clés étrangères** (`persister`) : une requête par table au lieu
  d'un aller-retour par ligne, indispensable contre une base distante.
- `etablissements.py` — **Université d'Abomey-Calavi toujours créée en premier (code UP01)**,
  quel que soit `--scale`, avec ses vraies entités (FADESP, FASEG, IFRI, EPAC, FSS, FLLAC,
  FAST) ; EP/ES/UP avec la taxonomie béninoise (`taxonomie.py`), A+ `admin.<code>@...`,
  référentiels de coefficients nationaux.
- `recrutement.py` — poste → candidatures notées (rejet automatique sous le seuil) → verdict
  casier CONFORME → **un** contrat par poste (POURVU) → signature ; reconductions dans la
  fenêtre de 30 jours ; postes encore ouverts avec casiers à examiner et contestations.
- `scolarite.py` — familles (nom du tuteur, fratries), âge conforme au niveau, consentement
  parental horodaté pour les moins de 16 ans uniquement (Art. 446), capacité respectée.
- `pedagogie.py` / `evaluations.py` — contenus par des enseignants **affectés**, cours PDF avec
  texte extrait, quiz et notes cohérents avec le niveau de chaque élève, **bulletin calculé
  comme l'application**, El Professor (4 personas, alertes), vie scolaire.
- `vie_classe.py` — messagerie selon les règles de DM, sessions live (tableau en coordonnées
  normalisées, capture rendue par `rendu_tableau.py`).
- `services.py` / `economie.py` — actes, tickets, billets, micro-jobs, marketplace et
  Coffre-fort avec les vraies transitions (paiement, validation tacite, reversement exigeant
  un numéro Mobile Money, validations parentales liées à de vraies dépenses).
- `demo.py` — scénarios **garantis** pour les comptes de démonstration (chaque écran et chaque
  file d'administration a quelque chose à montrer).
- `fichiers.py` — vrais fichiers générés (pymupdf) et téléversés **une fois** sur LuluFiles ;
  sans LuluFiles, aucune donnée n'exige de fichier (jamais d'identifiant fictif).

`scripts/verifier_seed.py` (lancé automatiquement en fin de seed) relit la base et contrôle
39 règles métier. Vérifié sur PostgreSQL : échelles 0,05 / 0,2 / 1,0 et trois graines, 39/39 ;
puis chaque compte de démonstration appelle tous les endpoints GET de l'API : aucune erreur
serveur. Échelle 1,0 : 30 établissements, 323 classes, ~5 200 élèves, ~8 700 comptes, 37 s en
local (sans fichiers). `scripts/seed_render.bat` : seed de la base Render depuis le poste
(aperçu, confirmation, clé de chiffrement des casiers de Render facultative, vérification).

## Phase 5 — Volet Professeur (UC-23 à UC-28)

Implémenté à partir d'un cahier des charges dédié (analyse de l'existant + cas d'utilisation manquants), sans redécrire ce qui existait déjà (mes classes, cours, devoirs, sessions live "coquille", contrôleur, micro-jobs, messagerie).

### app/modules/vie_scolaire/ (UC-23, nouveau module)
- `models.py` — `EntreeVieScolaire` (`nature` : absence/retard/appreciation/incident/felicitation ; `matiere` nullable — None réservé au professeur principal/admin pour une entrée globale). **Historique immuable** : pas de PATCH/DELETE exposé, même logique que la messagerie.
- `router.py` — `POST/GET /classes/{id}/eleves/{id}/vie-scolaire`, `GET /classes/{id}/vie-scolaire` (vue d'ensemble, réservée PP/admin). Portée de lecture : un enseignant de matière ordinaire ne voit **que ses propres entrées** (`auteur_id == lui`) ; le professeur principal (nouveau flag `AffectationEnseignant.est_professeur_principal`) et l'admin voient tout ; tuteur/élève voient tout ce qui les concerne.

### app/modules/etablissements/ (UC-24, enrichi)
- `models.py` — `Classe.annee_academique` (format `YYYY-YYYY`, rentrée au 1er septembre — `annee_academique_courante()`) : une Classe devient une instance **annuelle** précise, ce qui suffit à scoper aussi affectations/inscriptions sans toucher à leur schéma (elles pointent déjà vers une Classe via `classe_id`). `AffectationEnseignant.est_professeur_principal` (bool, un seul par classe, invariant appliqué côté applicatif).
- `router.py` — `GET /mes-classes-affectees` enrichi (`SalleEnseignantOut` : établissement, effectif, année académique, flag PP), filtré sur l'année en cours par défaut (`toutes_annees=true` pour l'historique). `GET /classes/{id}/eleves` (nominatif, enseignant affecté ou admin). `POST /classes/{id}/professeur-principal` (A+/A++, exige une affectation préalable).

### app/modules/evaluations/ (UC-26, enrichi)
- `models.py` — `Devoir.nature` (formative/sommative — une formative est **exclue** du calcul du bulletin), `Devoir.sujet_lulufiles_file_id` (visible élève), `Devoir.bareme_document_lulufiles_file_id` (jamais exposé à l'élève, comme `bareme_reponse` — voir `DevoirProprietaireOut` vs `DevoirOut`), `Soumission.copie_image_lulufiles_file_id` (soumission alternative entièrement imagée).
- `router.py` — `POST /devoirs/{id}/sujet-document` et `.../bareme-document` (multipart, propriétaire), `POST /devoirs/{id}/soumissions/copie-image` (élève, alternative au formulaire texte) corrigée **holistiquement** (une seule note globale, pas de découpage par question — `FreeLLMClient.corriger_copie_image`, vision FreeLLM) à partir des barèmes par question concaténés ; `POST /soumissions/{id}/corriger-note-globale` (révision manuelle équivalente pour ce cas). Conception 100% additive : aucun endpoint existant modifié dans sa forme (JSON pur texte toujours supporté tel quel).
- `app/core/conversion.py` — `convertir_en_image()` déplacé de `recrutement/` vers `core/` (utilisé désormais par les deux modules).

### app/modules/pedagogie/ (UC-27, enrichi)
- `models.py` — `SessionElProfessorEnseignant`/`MessageElProfessorEnseignant` (plusieurs sessions par enseignant, pas un upsert unique comme côté élève — c'est un historique de conversations par sujet/élève), `AlerteElProfessor` (garde-fou de sécurité).
- `router.py` — `POST /el-professor-enseignant/sessions` (+ `.../messages`) : contexte élève construit à partir de la vie scolaire que **l'enseignant a lui-même le droit de voir** (jamais plus). `_detecter_signal_alerte()` : heuristique par mots-clés (maltraitance, violence, danger...) sur la question ET la réponse — si positive, la réponse inclut une recommandation d'escalade explicite et une `AlerteElProfessor` est préparée pour l'administration (`GET/POST /etablissements/{id}/alertes-el-professor`, `.../traiter`). `app/core/llm.py::FreeLLMClient.conseiller_enseignant()` — persona distincte de l'assistant élève.

### app/modules/cours_direct/ (UC-25, enrichi — le plus gros chantier)
- `models.py` — `PanneauTableau` (panneaux "coulissants"), `TraitTableau` (append-only : trait libre/texte/effacement, jamais muté — permet le rejeu "time-lapse" ET une convergence naturelle entre plusieurs rédacteurs simultanés sans collision), `PermissionEcritureTableau` (craie "prêtée" ou "accordée", révocable à tout instant), `DemandeCraie` (file d'attente), `CaptureTableauSession` (snapshot PNG à la clôture), `MessageSessionLive` (chat, salle sociale pré-cours incluse).
- `rendu_tableau.py` — rendu PNG via **PyMuPDF** (déjà une dépendance du projet, aucune nouvelle lib) : rejoue les traits dans l'ordre, un `EFFACEMENT` vide tout ce qui précède, rasterise le résultat.
- `router.py` — tout le cycle REST du tableau (état, ajout de trait/panneau, effacement, demandes/permissions de craie), chat de session, captures. `rejoindre_session_live` relâché : un élève peut rejoindre dès `PLANIFIEE` (salle sociale pré-cours), pas seulement `EN_COURS`.
- `realtime.py` — `GestionnaireConnexionsLive`, registre en mémoire des connexions WebSocket par session (mono-process — limite assumée, à revoir avec Redis pub/sub si multi-instance un jour). **Aucune logique métier dans le canal temps réel** : les mutations passent toujours par les endpoints REST (validés, journalisés), qui diffusent ensuite l'événement résultant aux clients connectés — le WebSocket ne fait que relayer.
- **Choix technique tranché pour l'audio/vidéo réel** (jusqu'ici différé, jeton `uuid4()` placeholder) : **signalisation WebRTC en maillage (mesh)**, pas de SFU tiers — adapté aux effectifs d'une classe, relayé via le même canal WebSocket (`WS /ws/sessions-live/{id}`, type `webrtc_signal`). Décision qui évite d'introduire une dépendance d'infrastructure lourde (SFU managé ou self-hosted) pour ce premier jet ; à revoir si des sessions à très large effectif apparaissent (le maillage dégrade au-delà d'une poignée de flux vidéo simultanés).

### Migrations (0006 à 0010)
Chaîne vérifiée **upgrade ET downgrade contre un vrai Postgres** (instance jetable, cette fois disponible dans l'environnement de dev). Un bug réel trouvé et corrigé au passage : `0008_evaluations_enrichies.py` faisait un `add_column` avec un `sa.Enum` sur une table déjà existante — contrairement à un `create_table`, cela n'émet PAS automatiquement le `CREATE TYPE` Postgres (premier cas du projet à ajouter une colonne Enum après coup plutôt qu'à la création de sa table) ; corrigé via `postgresql.ENUM(...).create(op.get_bind(), checkfirst=True)` explicite avant l'`add_column`.

**Limite assumée découverte à cette occasion (pré-existante, pas causée par ce lot)** : `alembic_version.version_num` est resté sur le type `VARCHAR(32)` par défaut alors que les revision id de ce projet sont des chaînes descriptives longues (ex. `0003_etablissements_geolocalisation`, 36 caractères) — la chaîne de migrations plante dès `0003` sur un Postgres fraîchement initialisé (`StringDataRightTruncation`) sans un premier élargissement manuel de cette colonne. N'affecte que l'initialisation d'une base neuve depuis zéro (une base déjà migrée en place n'est pas concernée) ; à corriger avant tout nouveau déploiement partant d'une base vide.

**184 tests** (183 passants + 1 pré-existant dépendant de l'environnement — `test_parcours_complet_de_la_phase_1`, webhook Kkiapay, échoue seulement en l'absence de `KKIAPAY_SECRET` configuré, sans rapport avec ce lot).

**Non fait dans ce lot (limites assumées, à reprendre)** :
- `scripts/seed_mega.py` n'a pas été étendu pour peupler les nouvelles tables (vie scolaire, tableau, El Professor enseignant) — le seed reste utilisable tel quel pour les Phases 1 à 4.
- L'enregistrement vidéo consultable comme un cours (rejeu complet post-séance) n'est pas fait : le choix "maillage sans SFU" ne permet structurellement pas un enregistrement serveur des flux — seul le tableau (traits + capture PNG) est rejouable/consultable après coup.
- L'intégration automatique d'une capture de tableau dans le cahier de textes ("Mes cours") reste un P2 : les captures sont consultables via `GET /sessions-live/{id}/captures`, pas encore rattachées à un `Cours`.

## Phase 6 — Volet Élève/Tuteur (UC-29 à UC-38)

Implémenté à partir d'un cahier des charges dédié (parité fonctionnelle avec les autres profils + innovations), même méthode que la Phase 5 : rien ne redécrit ce qui existait déjà (inscriptions, devoirs, marketplace, micro-jobs, actes...).

### Corrections de portée (UC-29)
- `cours_direct/router.py::lister_sessions_live` acceptait `TUTEUR` dans `require_roles` **sans jamais vérifier sa portée réelle** (contrairement à ELEVE/ENSEIGNANT juste en dessous) — un tuteur authentifié pouvait lister les sessions de N'IMPORTE QUELLE classe. Corrigé par `_verifier_tuteur_a_un_enfant_dans_la_classe()`.
- `billetterie/router.py` : achat/paiement/remboursement de billet strictement réservés à `billet.utilisateur_id == utilisateur.id`, empêchant un tuteur d'acheter/gérer un billet pour son enfant. Ajout de `BilletAchatRequest(eleve_utilisateur_id)` + `_resoudre_beneficiaire_billet()`/`_verifier_proprietaire_ou_tuteur_billet()` (rétrocompatible : payload optionnel).

### Parité fonctionnelle (UC-30/31/34)
- `inscriptions/router.py` — `professeur_principal_nom/prenom` exposé sur `InscriptionAvecEleveOut`/`EleveMeOut` (le tuteur/élève ne pouvait identifier aucun contact référent).
- `evaluations/router.py` — `TUTEUR` ajouté à `obtenir_devoir`/`lister_devoirs`/`obtenir_soumission` (vérification `eleve.tuteur_id`), nouvel endpoint `GET /devoirs/{id}/soumission-de/{eleve_utilisateur_id}` (suivi direct sans jongler avec les IDs de soumission).
- `marketplace/router.py` — `GET /mes-enfants/{id}/marketplace/annonces` et `.../transactions` (TUTEUR, lecture seule, jamais de publication/achat pour le compte de l'enfant — cohérent avec le seuil d'âge ≥16 ans déjà en vigueur).

### app/modules/pedagogie/ (UC-32/37, enrichi)
- `SessionElProfessorTuteur`/`MessageElProfessorTuteur` : même mécanique que côté enseignant (fils multiples, pas d'upsert unique), mais `eleve_utilisateur_id` **toujours requis** (un tuteur consulte toujours à propos d'un enfant précis). `AlerteElProfessor` gagne `origine` (ENSEIGNANT/TUTEUR/FAMILLE) + `eleve_utilisateur_id` dénormalisé pour une requête directe côté tuteur (`session_id` cesse d'être une vraie FK — même pattern que `DesignationControleur.evenement_id`).
- **El Professor Famille (UC-37, innovation)** — `SessionElProfessorFamille`/`MessageElProfessorFamille` : fil **partagé** entre un tuteur et son enfant, toujours créé par le tuteur (qui "invite" l'enfant), inutilisable (aucun message des deux côtés) tant que l'enfant n'a pas explicitement appelé `POST .../rejoindre` — jamais un fil individuel qui bascule seul en mode famille. Garde-fou renforcé : un signal de danger détecté dans un fil familial crée une alerte `origine=FAMILLE`, **exclue** de `GET /mes-enfants/{id}/alertes-el-professor` (le tuteur peut être la source du danger) — visible uniquement de l'administration.
- `FreeLLMClient.conseiller_tuteur()`/`conseiller_famille()` (persona dédiée, la seconde s'adresse explicitement au bon interlocuteur via un paramètre `qui_parle`).

### app/modules/cours_direct/ (UC-33, enrichi)
- `ResumeSessionLive` : résumé texte généré par FreeLLM (`resumer_session_live()`) à la clôture d'une session (`terminer_session_live`), à partir du chat **et** du contenu textuel du tableau (blocs TEXTE uniquement — un trait libre n'a pas de représentation textuelle). Jamais un flux vidéo/audio (qui n'existe pas côté serveur, voir Phase 5/`realtime.py`). `GET /sessions-live/{id}/resume` (TUTEUR, vérifie qu'un de ses enfants a bien participé via `ParticipationLive`) — le tuteur ne rejoint jamais la session en direct.

### app/modules/coffre_fort/ (UC-35, nouveau module — innovation)
- `PlafondFamilial` (config opt-in par enfant : plafond hebdomadaire et/ou seuil de validation, **aucun par défaut** — l'autonomie actuelle de l'élève n'est jamais réduite sans action explicite du tuteur), `ValidationParentale` (s'intercale entre la création d'une dépense et l'amorçage de son paiement quand le seuil est dépassé — jamais un blocage silencieux, ni une altération du statut existant de l'offre/transaction/demande elle-même), `AlerteDepassementPlafond` (notification passive, jamais bloquante, quand le plafond hebdomadaire est dépassé).
- `service.py::evaluer_depense()` appelé juste avant l'amorçage du paiement dans **trois modules** (`micro_jobs`, `marketplace`, `actes`) — dupliqué plutôt qu'importé en boucle, cohérent avec le style du projet. `construire_releve_financier()` : relevé consolidé lecture seule (gains micro-jobs + ventes marketplace − achats − dépenses micro-jobs − frais d'actes), disponible même sans configuration.

### app/modules/radar_familial/ (UC-36, nouveau module — innovation)
- Aucune table : digest hebdomadaire généré **à la demande** (pas de push), à partir de faits déjà établis ailleurs (vie scolaire, devoirs corrigés, sessions live suivies, activité financière si le Coffre-fort est actif) assemblés en lignes de citation datées par `construire_sources_radar_familial()`, puis reformulés en résumé narratif par `FreeLLMClient.generer_digest_famille()` — qui ne reçoit **que** cette liste et ne peut donc pas halluciner un fait absent. Sans le moindre fait sur la période, aucun appel LLM n'est fait.

### app/modules/passeport_competences/ (UC-38, nouveau module — innovation)
- Aucune nouvelle saisie : agrège des données déjà produites ailleurs (`TentativeQuiz` réussies dédupliquées par quiz, `Cours` des classes où l'élève a été validé, moyennes par matière recalculées simplement à partir des soumissions corrigées — volontairement plus simple que le bulletin officiel pondéré). Badges dérivés directement de ces agrégats (jamais un critère arbitraire non traçable) — contrairement aux médailles actuellement **hardcodées côté frontend** (`gamification.tsx`/`EleveDashboard.tsx`, données de démo, pas de calcul réel).
- `pdf.py` : export PDF via **PyMuPDF** (déjà en place pour le rendu du tableau collaboratif, aucune nouvelle dépendance — `reportlab` listé dans `requirements.txt` mais jamais utilisé nulle part dans le projet). Upload LuluFiles standard.
- `GET/POST /eleves/me/passeport(/export-pdf)` et `.../mes-enfants/{id}/passeport(/export-pdf)` (TUTEUR).

### Migrations (0011 à 0014)
Chaîne vérifiée **upgrade ET downgrade contre un vrai Postgres**. Deux bugs réels trouvés et corrigés :
- `0012_coffre_fort_familial.py` : deux `create_table` distincts réutilisant le **même nom** d'enum Postgres (`moduledepensecoffrefort`) — le premier le crée automatiquement (checkfirst=False dans ce chemin d'alembic, symétrique du bug déjà documenté en Phase 5 pour `add_column`), le second tentait de le recréer et échouait (`DuplicateObject`). Corrigé en passant `postgresql.ENUM(..., create_type=False)` pour la seconde table.
- `0014_el_professor_famille.py` : le downgrade tentait un `ALTER COLUMN ... TYPE` sur `alertes_el_professor.origine` (retrait de la valeur d'enum `FAMILLE`, qui exige de recréer le type) alors qu'un `DEFAULT` était encore actif sur la colonne — Postgres refuse (`DatatypeMismatch`). Corrigé en retirant le `DEFAULT` avant l'`ALTER TYPE` et en le rétablissant après.

**213 tests passants** (+1 pré-existant dépendant de l'environnement, `KKIAPAY_SECRET` absent — voir Phase 5), aucune régression.

**Non fait dans ce lot (limites assumées)** :
- `scripts/seed_mega.py` n'a pas été étendu pour peupler les nouvelles tables (Coffre-fort, El Professor Famille, résumés de session live).
- Le Radar familial (UC-36) n'a pas de mécanisme de notification poussée (email/push) — consultation à la demande uniquement, cohérent avec ADR-002 (FreeLLM sans SLA, pas d'envoi automatique à heure fixe pour des milliers d'élèves).
- Le Coffre-fort (UC-35) ne couvre que le déclenchement du blocage/de l'alerte à l'amorçage du paiement ; aucune UI n'existe encore pour que le tuteur configure ses plafonds (à faire côté frontend).

## Dernière synchronisation
2026-09-26 (Phase 5, backend) — Backend complet du lot admin ministériel (UC-23 à UC-38,
voir `../docs/cahier-des-charges-refonte-admin-ministeriel.md` et
`../docs/diagrammes-uml-phase-5-admin-ministeriel.md`), migration `0006_supervision_min`
(appliquée et vérifiée upgrade+downgrade contre un vrai Postgres local, disponible pour la
première fois dans cet environnement de dev — voir aussi le bugfix `alembic_version`
ci-dessous). Changements : `Etablissement.description`/`.actif` (+ `PATCH
/etablissements/{id}/description`, `POST /etablissements/action-groupee`, suspension
filtrée hors des vitrines publiques) ; `ReferentielCoefficient` éditable directement par
l'A++ (`PATCH /referentiels-coefficients/{id}`) et validation groupée (`POST
.../valider-lot`) ; micro-jobs : `GET /contestations-micro-job` et `GET
/missions-micro-job/a-reverser` (files d'arbitrage enrichies — mission/offre/parties —
remplaçant la saisie manuelle d'un id) ; `Utilisateur.actif` (+ `GET /admin/utilisateurs`,
suspension/réactivation, blocage dans `get_current_active_user`, auto-suspension
interdite) ; `Cours`/`Devoir` masquables non destructivement (`masque_par_id`/`masque_le`,
`GET /admin/cours`/`/admin/devoirs`, exclus de la vue élève) ; `GET /admin/evenements` +
annulation d'urgence par l'A++ (RBAC déjà ouvert via `_est_organisateur`, aucun changement
nécessaire là) ; nouveau module `app/modules/audit/` journalisant toute action sensible de
l'A++. **10 nouveaux tests** (`tests/test_admin_ministeriel.py`), **163 tests passants au
total**, aucune régression. Prochaine étape : frontend (DataTable générique réutilisable +
écrans établissements/référentiels/arbitrage/utilisateurs/contenus/événements).

2026-09-26 (Phase 5, bugfix migration) — En appliquant les migrations `0002`-`0005` contre
un Postgres réel pour la première fois (jamais fait jusqu'ici, voir les notes "pas encore
vérifié contre un vrai Postgres" laissées par les phases précédentes), découverte d'un vrai
bug bloquant : `alembic_version.version_num` est un `VARCHAR(32)` par défaut, or
l'identifiant de la révision `0003_etablissements_geolocalisation` fait 36 caractères —
`alembic upgrade head` échouait silencieusement à cette transition. Corrigé en élargissant
la colonne à 255 dans la migration `0002` (avant le premier id trop long), pas dans `0001`
qui est déjà appliqué en production. Migrations `0002` à `0006` désormais toutes vérifiées
upgrade **et** downgrade contre un Postgres réel.

2026-09-26 (Phase 6, backend) — Backend complet pour le volet Élève/Tuteur (UC-29 à
UC-38, voir section dédiée ci-dessus) : corrections de portée RBAC, parité fonctionnelle
avec les autres profils, et cinq innovations (El Professor Famille, Coffre-fort
familial, résumé asynchrone de session live, Radar familial, Passeport de compétences).
Trois nouveaux modules (`coffre_fort`, `radar_familial`, `passeport_competences`),
migrations `0011` à `0014` vérifiées upgrade/downgrade contre un vrai Postgres (deux
bugs réels trouvés et corrigés au passage, voir section Migrations). **213 tests
passants**, aucune régression. Frontend de ce lot pas encore commencé.

2026-09-26 (encore plus tard, refonte RBAC) — Audit complet des 5 rôles sur les 14 modules
backend (demandé explicitement, pas préventif) a révélé 3 trous : (1) A++ bloqué (403) sur
~30 endpoints dans 9 modules à cause de 4 copies indépendantes d'un helper
`_verifier_admin_de_l_etablissement` codées en `if role != ADMIN_ETABLISSEMENT: refuse`, qui
ne laissaient jamais passer A++ — centralisées en une seule fonction partagée
(`core/deps.py::verifier_portee_etablissement`) ; (2) deux endpoints sans AUCUNE vérification
de portée (`evaluations.obtenir_devoir`, `evaluations.valider_passage`) et
`lister_referentiels` qui exposait les propositions de coefficient d'un établissement
concurrent à un A+ — corrigés ; (3) aucune table ne liait un enseignant à ses classes
précises (seul `Contrat`, à l'échelle de l'établissement entier, existait) — nouvelle table
`AffectationEnseignant` (migration `0005`) + endpoints de gestion (voir section
`app/modules/etablissements/` ci-dessus), devenue le vrai filtre pour créer/gérer
cours/quiz/devoirs/sessions live (remplace `_verifier_enseignant_rattache` établissement-large
dans `pedagogie`/`cours_direct`/`evaluations`, désormais centralisée dans `pedagogie/router.py`
et importée par les deux autres). `scripts/seed_mega.py` crée désormais une
`AffectationEnseignant` par classe peuplée. Nouveau fichier `tests/test_rbac_portee.py`
verrouillant les 3 chantiers ; fixtures/tests e2e existants mis à jour en conséquence.
**151 tests passants**, aucune régression.

2026-09-26 (encore plus tard, marketplace, seed) — `scripts/seed_mega.py` étendu pour peupler la Phase 4 (marketplace étudiante) : `creer_marketplace_pour_etablissement`, appelée pour chaque établissement juste après `creer_visite_virtuelle`. Génère annonces + photo (placeholder LuluFiles) + signalements occasionnels + transactions couvrant tout le cycle de séquestre (y compris contestations acceptées/rejetées), avec le statut de l'annonce toujours recalculé en cohérence avec sa transaction. Vérifié isolément sur 80 graines aléatoires (SQLite en mémoire) avant intégration, aucune erreur, les 8 statuts de transaction et les 3 décisions de contestation tous atteints.

2026-09-26 (encore plus tard, marketplace, e2e) — Étape 5 (validation de bout en bout) close pour la Phase 4 : `tests/test_e2e_parcours_phase4_marketplace.py` rejoue UC-20 → UC-21 → UC-22 dans l'ordre réel (annonce → signalement traité → réservation → paiement séquestré via webhook → remise → confirmation → reversement au vendeur par l'A+), un seul jeu d'établissement/classe/vendeur/acheteur — passé du premier coup. Scan de sécurité de la méthode `lucio-dev` exécuté (`bandit`+`pip-audit` installés pour l'occasion) : bandit 0 problème sur le nouveau module ; pip-audit signale 2 CVE sur `ecdsa` 0.19.2 (`PYSEC-2026-1325`, dépendance transitive de `python-jose`, sans fix disponible) — non bloquant, HS256 utilisé partout sur cette plateforme (jamais le chemin ECDSA vulnérable), dépendance antérieure à ce lot. Relecture manuelle de la checklist sécurité (IDOR, montants côté serveur, non-contournement du séquestre) sans anomalie trouvée. **143 tests passants au total**, aucune régression. Migration `0004` toujours pas vérifiée contre un vrai Postgres (aucune instance disponible dans cet environnement de dev) — à faire avant le déploiement.

2026-09-26 (encore plus tard, marketplace) — Backend complet pour la Phase 4 (marketplace étudiante, UC-20/21/22) : module `app/modules/marketplace/` (annonces + photos LuluFiles + signalements + transactions/séquestre + contestations), migration `0004_marketplace.py`, webhook Kkiapay étendu (`_confirmer_transaction_marketplace`). Réutilise systématiquement des helpers déjà existants plutôt que d'en dupliquer : `AGE_MAJORITE_NUMERIQUE`/`_age_a` (inscriptions), `verifier_admin_de_l_etablissement` (contrôle d'accès), le pattern séquestre/validation tacite d'UC-18 et le pattern upload multipart de `recrutement.postuler`. Arbitrage et reversement confiés à l'A+ de l'établissement (pas l'A++, contrairement aux micro-jobs) car vendeur et acheteur sont toujours du même établissement. **11 nouveaux tests** (`tests/test_marketplace.py`), **141 tests passants au total**, aucune régression. Migration vérifiée par `alembic heads`/`history` (chaîne cohérente depuis `0003`) ; pas encore appliquée contre un Postgres réel dans cet environnement (aucune instance locale disponible ici) — à faire avant l'étape 5 (validation de bout en bout) ou le déploiement.

2026-09-26 (encore plus tard) — Squash des 22 migrations Alembic en une seule
(`0001_schema_initial.py`), déclenché par un vrai échec de déploiement Render
(`UndefinedObject: type "statutsoumission" does not exist`, causé par l'ancienne
`0010_formulaires_llm.py` qui `DROP TYPE` puis recréait aussitôt une table
l'utilisant). Générée par `alembic revision --autogenerate` contre une base Postgres
vide (versions/ temporairement vidée pour forcer une comparaison depuis rien),
vérifiée upgrade **et** downgrade sur une base fraîche avant commit. Voir la section
`alembic/versions/` ci-dessus pour le détail et l'impact sur les bases locales
existantes.

2026-09-26 (plus tard) — Ajout de `scripts/seed_mega.py`, seed de développement peuplant
toutes les tables applicatives à volume « grandeur nature » (voir section dédiée
ci-dessus). Aucun changement du schéma ni des routers — outil de développement pur.

2026-09-25 — Phase 2/3 : backend complet pour les 9 UC (tickets transport/cantine, contrôle d'accès, billetterie, messagerie, El Professor, cours vidéo, cours en direct, visites 3D/drone, micro-jobs+séquestre), 8 migrations appliquées en réel, **et validation de bout en bout** : `tests/test_e2e_parcours_phase2_3.py` rejoue les 9 UC dans un ordre d'usage réel avec les mêmes établissement/classe/enseignant/élève/tuteur, paiement Kkiapay réellement bouclé (amorcer + webhook) à chaque étape payante — passé du premier coup après deux ajustements mineurs. **120 tests passants** (75 Phase 1 + 45 Phase 2/3), aucune régression. Webhook Kkiapay extrait de `actes/` vers un module `paiements/` partagé.
