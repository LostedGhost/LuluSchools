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
- `scripts/` — outils one-shot serveur (seed du tout premier compte A++) et `seed_mega.py` (voir section dédiée ci-dessous)
- `tests/` — pytest, SQLite en mémoire (`StaticPool` pour partager la connexion entre threads), tous les services externes mockés (Brevo/FreeLLM/LuluFiles) — aucun appel réseau réel dans la suite. `test_e2e_parcours_complet.py` rejoue tout le parcours UC-01 à UC-10 dans l'ordre réel (Phase 1), `test_e2e_parcours_phase2_3.py` fait de même pour UC-11 à UC-19 (Phase 2/3), en plus des tests unitaires par module

## Fichiers clés

### app/core/
- `config.py` — `Settings` (pydantic-settings) ; lit `.env` à la **racine du dépôt**, chemin calculé depuis `__file__` (pas depuis le cwd — un premier bug l'avait fait chercher `backend/.env`, corrigé).
- `database.py` — engine SQLAlchemy, `SessionLocal`, `Base` (métadonnées partagées par tous les modules), dépendance `get_db`.
- `security.py` — hash Argon2 des mots de passe, génération/hash des OTP (HMAC-SHA256 salé, jamais stockés en clair), génération de mot de passe temporaire, création/décodage JWT (access + refresh, HS256).
- `deps.py` — `get_current_user` (décode le JWT, charge l'utilisateur), `require_roles(*roles)` (RBAC par dépendance FastAPI), `api_error()` (fabrique une `HTTPException` au format `{"error": {...}}` du contrat).
- `email.py` — `BrevoEmailClient.send_otp_email` / `.send_temporary_credentials_email`, appels HTTP directs à l'API Brevo. Injecté via `Depends(get_email_client)` pour rester substituable en test. Envoie `htmlContent` (document HTML complet avec branding, pas un fragment `<p>` nu — un fragment sans `<!DOCTYPE html>/<html>/<body>` cassait le rendu chez certains clients mail) et `textContent` (secours texte seul). **Piège réel rencontré** : `BREVO_SENDER_EMAIL` doit être une adresse *vérifiée* dans le compte Brevo (Expéditeurs & IP) — avec le placeholder par défaut (`no-reply@luluschools.example`, domaine `.example` non routable), Brevo accepte la requête API (201/202, pas d'erreur visible côté appli) mais ne délivre jamais le mail.
- `files.py` — `LuluFilesClient.upload` / `.get_signed_link` (ADR-003), injecté via `Depends(get_files_client)`.
- `llm.py` — `FreeLLMClient.noter_document` : envoie une image en vision via l'API compatible OpenAI de FreeLLM, parse un score 0-100 depuis la réponse texte (ADR-002). Injecté via `Depends(get_llm_client)`.
- `crypto.py` — `chiffrer_bytes`/`dechiffrer_bytes` (Fernet) pour le casier judiciaire stocké en base (`recrutement/router.py`) ; la clé `CASIER_JUDICIAIRE_ENCRYPTION_KEY` est hashée (SHA-256) avant usage pour accepter n'importe quel format de secret (dont le base64 standard généré par `generateValue: true` de Render, pas garanti urlsafe comme l'exige Fernet).

### app/modules/identite/
- `models.py` — `Utilisateur` (table de base commune à tous les rôles ; `login_id` = e-mail pour tuteur/enseignant/admin, matricule pour un élève), `Tuteur`, `OtpVerification`, enum `RoleUtilisateur`.
- `router.py` — `router` (`/auth/tuteurs`, `/auth/tuteurs/verify-otp` — UC-01) + `auth_router`/`me_router` (`/auth/login`, `/auth/refresh`, `/auth/change-password`, `/me`).
- `schemas.py` — schémas Pydantic stricts (`extra="forbid"`, anti mass-assignment), validateur de force de mot de passe partagé création/changement.

### app/modules/etablissements/
- `models.py` — `Etablissement`, `AdminEtablissement` (lien 1-1 vers `Utilisateur`), `Classe`, `EtablissementPhoto` (ADR-009, migration `0021` — ne stocke que `lulufiles_file_id` + `ordre`, jamais d'URL brute), enums `TypeEtablissement`/`StatutEtablissement`/`PolitiqueDepassement`.
- `router.py` — `POST/GET /etablissements` (A++ seul pour créer, provisionne aussi le premier compte A+ avec mot de passe temporaire), `GET /etablissements/mon-etablissement` (point d'entrée du frontend A+ — sans lui, un A+ n'a aucun moyen de savoir quel établissement il administre, ce n'est pas exposé sur `MeOut` ; **attention à l'ordre des routes** : déclaré avant `GET /{etablissement_id}` sinon ce dernier capturerait `mon-etablissement` comme un id), `POST/GET /etablissements/{id}/classes` (A+, avec vérification stricte que l'admin administre bien CET établissement — anti-IDOR).
- **Endpoints publics (sans authentification)** — avec `GET /health` (`app/system/router.py`), les seuls de tout le backend ; tous déclarés avant `GET /{etablissement_id}` pour l'ordre des routes (ADR-009) :
  - `GET /etablissements/vitrine-publique` — teaser léger pour la landing page (3 établissements en avant, quelques postes ouverts, totaux globaux). N'expose que des champs non sensibles (`EtablissementVitrineOut`/`PosteVitrineOut`/`VitrinePubliqueOut`, jamais `code_etablissement` ni d'email d'admin). Importe `Poste`/`StatutPoste` depuis `modules/recrutement/models.py` (couplage en lecture seule, cohérent avec l'import déjà existant de `modules/messagerie/models`).
  - `GET /etablissements/annuaire-public?type=&q=&limit=&offset=` — annuaire complet paginé, pour la page dédiée `/etablissements` du frontend (jamais la landing page — la plateforme a vocation nationale). **`limit` plafonné cote serveur a 60 quel que soit ce qui est demandé**, ne jamais faire confiance a un client pour borner sa propre requête.
  - `GET /etablissements/{id}/photos-publiques` — résout les liens signés LuluFiles à la demande, **appelé uniquement pour un établissement précis** (jamais en boucle sur toute une page d'annuaire, pour ne pas multiplier les appels vers LuluFiles — voir le risque de quota déjà signalé sur ce service). `POST`/`DELETE /etablissements/{id}/photos` (A+ de l'établissement, `_verifier_admin_de_l_etablissement`, max 8 photos) gèrent l'upload/suppression réelle.

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
- `seed_mega.py` — seed de développement « grandeur nature » : peuple **toutes** les tables applicatives (35+ tables, Phase 1 + Phase 2/3) avec un volume représentatif du système éducatif béninois. Voir section dédiée ci-dessous.

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

## Seed de développement grandeur nature (`scripts/seed_mega.py`)

Créé sur demande explicite de l'utilisateur (« tests grandeur nature »), pour disposer d'un
jeu de données réaliste couvrant les UC implémentés sans passer par des dizaines de
comptes créés manuellement. Usage : `cd backend && python scripts/seed_mega.py --yes`
(`--scale` ajuste tous les volumes, `--seed` change le tirage aléatoire — reproductible).
Étendu le 2026-09-26 pour couvrir la Phase 4 (marketplace étudiante, UC-20/21/22) en plus
des 18 UC des Phases 1/2/3.

**Ce qu'il fait** : réinitialise entièrement le schéma (`Base.metadata.drop_all` puis
`create_all` — même technique que `tests/conftest.py` sur SQLite, appliquée ici à Postgres)
puis insère directement via SQLAlchemy (sans passer par les endpoints HTTP, pour la vitesse)
~30 établissements (10 EP, 10 ES moitié général/moitié technique, 10 UP moitié
public/moitié privé), avec la vraie taxonomie béninoise : niveaux Maternelle→CM2, séries
générales A1/A2/B/C/D et techniques F2-F4/G1-G3 encodées directement dans `Classe.niveau`
(pas de colonne `filiere` dédiée — le modèle n'en a pas, volontairement non modifié pour
un simple seed), filières universitaires réalistes (Droit, Génie Civil, Informatique de
Gestion, etc.) avec leurs propres matières. Résultat typique (`--scale 1.0`) : 370 classes,
~4400 élèves/inscriptions, ~6200 utilisateurs, et un volume cohérent sur les 40 tables
restantes (recrutement, pédagogie, évaluations, actes, messagerie, cours en direct,
transport/cantine, billetterie, micro-jobs, visites virtuelles, **marketplace étudiante**)
— recensement exact dans le récapitulatif imprimé en fin d'exécution. Tous les comptes
partagent le mot de passe `Password1!` (mot de passe permanent, flux OTP volontairement
court-circuité).

**Marketplace (UC-20/21/22, ajouté le 2026-09-26)** : par établissement ayant au moins deux
élèves ≥16 ans avec compte (seuil dupliqué de `AGE_MAJORITE_NUMERIQUE`, pas d'import d'un
module de router dans ce script qui ne dépend sinon que de `models` purs), génère des
annonces réalistes (fournitures, manuels, uniformes, électronique...), un signalement
occasionnel (15 %, dont 60 % déjà traités par l'A+), puis pour 60 % des annonces une
transaction couvrant tout le cycle de vie du séquestre (`en_attente_paiement` → `finalisee`
ou `remboursee`/`annulee`), y compris les deux issues d'une contestation (acceptée →
remboursement, rejetée → transaction confirmée) — le statut de l'`Annonce` liée est toujours
recalculé en cohérence (`reservee`/`vendue`/`disponible`), jamais laissé désynchronisé de sa
transaction. Vérifié par un script isolé (SQLite en mémoire, hors périmètre Postgres/Alembic
de ce seed) rejouant la fonction sur 80 graines aléatoires différentes : les 8 statuts de
transaction et les 3 décisions de contestation sont tous atteints sans erreur.

**Piège réel rencontré et corrigé** : un premier jet faisait un seul `db.add()` par ligne
puis un unique `commit()` final, en supposant que SQLAlchemy trierait automatiquement les
INSERT par dépendance de clé étrangère (comportement bien réel... mais seulement quand des
`relationship()` relient les mappers). Aucun modèle de ce projet n'utilise `relationship()`
pour ses clés étrangères (que des colonnes id brutes) : sans elles, l'ordre d'insertion
n'est pas garanti, ce qui provoquait des `ForeignKeyViolation` aléatoires (reproduit dans un
cas minimal à 2 tables sans aucune complexité annexe). Corrigé en remplaçant tout `db.add`
par un helper `add()` qui `flush()` immédiatement après chaque ajout — chaque ligne devient
réelle dans la transaction en cours avant que la suivante ne puisse la référencer, sans rien
perdre de l'atomicité globale (un seul `commit()` final).

**Second piège** : `Base.metadata.drop_all`/`create_all` ne touchent jamais la table
`alembic_version` (hors de `Base.metadata`) — après un seed, `alembic upgrade head`
croirait la base vierge et rejouerait toutes les migrations sur des tables déjà présentes.
Le script aligne donc `alembic_version` sur `head` via `alembic.command.stamp(..., purge=True)`
juste après le reset (`purge=True` efface la table plutôt que de calculer un delta depuis
son contenu courant — nécessaire ici car l'historique de migrations de ce projet a été
squashé en une seule révision (`0001_schema_initial`), rendant tout ancien contenu de
`alembic_version` incompatible).

**Limites assumées** : `etablissement_photos` reste vide (nécessiterait de vrais envois
LuluFiles, hors périmètre d'un seed hors-ligne) ; `otp_verifications` reste vide (flux OTP
volontairement court-circuité, son absence est l'état normal en régime établi) ;
`photos_annonce_marketplace` réutilise le même identifiant LuluFiles factice que les cours
PDF/vidéo (`LULUFILES_ID_PLACEHOLDER`), jamais un vrai envoi.

## Dernière synchronisation
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
