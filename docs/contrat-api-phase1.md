# LuluSchools — Contrat d'API, Phase 1

Posé avant le premier endpoint (étape 3 de la méthode `lucio-dev`), dérivé du diagramme de classes validé (`docs/diagrammes-uml-phase1.md`) et des cas d'utilisation (`docs/cas-utilisation-phase-1.md`). Les schémas de requête/réponse détaillés (champ par champ) seront précisés juste avant l'implémentation de chaque endpoint à l'étape 4, mais la liste des ressources, les méthodes et les conventions ci-dessous sont fixées maintenant et ne doivent plus bouger implicitement au fil du code.

## Conventions

- Base : `/api/v1`
- Auth : `Authorization: Bearer <JWT access token>`, sauf endpoints marqués **public**.
- Dates : ISO 8601 UTC.
- Listes : pagination par `?page=&page_size=`, réponse `{ "items": [...], "total": int, "page": int, "page_size": int }`.
- Ressource unique : renvoyée directement en JSON (pas d'enveloppe).
- Erreurs : `{ "error": { "code": "string", "message": "string", "details": {} } }` avec le code HTTP approprié (400 validation, 401 non authentifié, 403 non autorisé, 404 introuvable, 409 conflit d'état, 422 entité non traitable, 500 erreur serveur).
- Chaque endpoint est annoté du rôle RBAC minimal requis et du cas d'utilisation dont il découle.
- **Fichiers** (cours, documents de candidature hors casier judiciaire, soumissions de devoirs, actes académiques) : upload en `multipart/form-data` vers l'endpoint métier concerné (ex. `POST /candidatures/{id}/documents`), le backend relaie vers LuluFiles et stocke `lulufiles_file_id` (voir ADR-003) — jamais de clé LuluFiles côté client. Téléchargement via un lien signé à durée limitée : `GET /fichiers/{id}/lien` (rôle : selon rattachement au dossier) renvoie `{ "url": "...", "expires_at": "..." }`, jamais l'octet brut depuis notre API. Le casier judiciaire n'a pas de route de ce type — accès restreint hors API REST standard (cf. section "Hors contrat" ci-dessous).

## Système

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| GET | `/health` | **public, assumé** | — | Sonde de disponibilité (supervision/load balancer) : `200 {"status":"ok","checks":{"database":true}}` ou `503 {"status":"degraded","checks":{"database":false}}`. Pas de logique métier, pas d'authentification par choix documenté (checklist sécurité §8). |

## Identité et authentification

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/auth/tuteurs` | public | UC-01 | Crée un compte tuteur, déclenche l'envoi de l'OTP par e-mail (Brevo) |
| POST | `/auth/tuteurs/verify-otp` | public | UC-01 | Valide le code à 6 chiffres (10 min, 5 tentatives max), active le compte |
| POST | `/auth/login` | public | — | `identifiant` (e-mail pour tuteur/enseignant/admin, matricule pour un élève) + mot de passe → access + refresh token. Refusé (403) si le compte n'est pas encore vérifié. |
| POST | `/auth/refresh` | public (refresh token) | — | Renouvelle l'access token |
| POST | `/auth/change-password` | tout utilisateur authentifié | — | Change le mot de passe ; lève le drapeau `doit_changer_mot_de_passe` (utile pour les comptes élève provisionnés avec un mot de passe temporaire) |
| GET | `/me` | tout utilisateur authentifié | — | Profil de l'utilisateur courant |

## Établissements, classes, campagnes

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/etablissements` | A++ | — | Création d'un établissement (EP/ES/UP), attribue le code établissement (`EP01`, `ES01`, `UP01`…) ; crée aussi le premier compte A+ (mot de passe temporaire envoyé par e-mail, changement obligatoire à la première connexion). Le tout premier compte A++ n'a pas d'endpoint : il est provisionné une fois via `backend/scripts/seed_admin_ministeriel.py`, exécuté directement sur le serveur. |
| GET | `/etablissements` / `/etablissements/{id}` | tout utilisateur authentifié | — | Lecture |
| GET | `/etablissements/mon-etablissement` | A+ | — | L'établissement administré par l'A+ courant (non déductible de `GET /me`) |
| POST | `/etablissements/{id}/classes` | A+ | UC-02, UC-03 | Définit niveau, capacité, politique de dépassement |
| GET | `/etablissements/{id}/classes` | tout utilisateur authentifié | — | Lecture |

## Inscriptions

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/inscriptions` | Tuteur, ou Élève titulaire (réinscription sur son propre compte déjà existant) | UC-02 | Corps : `nom`, `prenom`, `date_naissance`, `classe_id`, `nationalite` (`nationale` \| `etrangere`, défaut `nationale`), `consentement_parental_donne`. Statut initial `soumise` ou `en_attente_consentement_parental` selon l'âge (peut être court-circuité par `consentement_parental_donne: true` à la soumission). |
| POST | `/inscriptions/{id}/consentement-parental` | Tuteur rattaché | UC-02 | Débloque une inscription en attente de consentement |
| POST | `/inscriptions/{id}/valider` | A+ (de l'établissement de la classe) | UC-02, UC-03 | Refusé (409) si consentement manquant ou classe complète (capacité atteinte, compte les inscriptions déjà `validee`). Génère le matricule (voir UC-03 : format universitaire `[nationalite:1][sequence:5][annee:2]` sur 8 caractères, format EP/ES `[cycle:1][nationalite:1][sequence:5][annee:2]` sur 9 caractères) et le compte élève (mot de passe temporaire envoyé au tuteur par e-mail). |
| POST | `/inscriptions/{id}/rejeter` | A+ | UC-02 | Motif obligatoire |
| GET | `/inscriptions/{id}` | Tuteur rattaché, ou A+ de l'établissement de la classe | UC-02 | Lecture (contrôle d'accès vérifié, pas seulement l'authentification — anti-IDOR) |
| GET | `/etablissements/{id}/inscriptions-a-valider` | A+ | UC-02 | Liste les inscriptions `soumise` en attente de validation pour l'établissement (écran A+) |
| GET | `/tuteurs/me/inscriptions` | Tuteur | UC-02 | Liste les enfants du tuteur courant et le statut de leurs démarches (nom/prénom/matricule inclus, pas d'aller-retour par enfant) |
| GET | `/eleves/me` | Élève | UC-02 | Profil de l'élève courant : matricule, nationalité, et classe actuelle (déduite de la dernière inscription validée) — point d'entrée du frontend élève |

## Recrutement et contrats

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| GET | `/etablissements/{id}/postes` | tout utilisateur authentifié | UC-04 | Liste les postes de l'établissement (découverte pour un enseignant candidat) |
| POST | `/etablissements/{id}/postes` | A+ | UC-04 | Définit les critères par type de document (coefficient, seuil minimal) |
| GET | `/postes/{id}` | tout utilisateur authentifié | UC-04 | Lecture |
| GET | `/postes/{id}/candidatures` | A+ de l'établissement du poste | UC-04, UC-05 | Toutes les candidatures du poste — nécessaire pour que l'A+ puisse créer un contrat (`POST /candidatures/{id}/contrat`) sans déjà connaître l'id de la candidature. Inclut `enseignant_nom`/`enseignant_prenom` (**ajouté a posteriori** : une candidature réduite à des identifiants était inexploitable pour une vraie décision de recrutement). |
| GET | `/mes-candidatures` | Enseignant | UC-04 | Historique des candidatures de l'enseignant courant |
| GET | `/mes-contrats` | Enseignant | UC-05 | Contrats de l'enseignant courant (statut, échéance) |
| GET | `/etablissements/{id}/contestations-en-attente` | A+ | UC-04b | Contestations `en_attente` de décision pour l'établissement |
| POST | `/postes/{id}/candidatures` | Enseignant | UC-04 | `multipart/form-data` : `types[]` + `fichiers[]` (un par critère du poste, exactement) + `casier_judiciaire` à part. Upload LuluFiles synchrone (nécessaire pour renvoyer les identifiants), mais la notation FreeLLM part **en arrière-plan** (`BackgroundTasks`, un appel réseau par document — pas de SLA, ADR-002) : la réponse renvoie les documents en `statut=en_attente` sans note, à relire via `GET /candidatures/{id}` une fois le traitement terminé. Le casier judiciaire est stocké localement, jamais sur LuluFiles (Art. 395). Si un document échoue à être noté, la candidature reste `en_evaluation` sans score, en attente d'une révision manuelle (voir `GET /candidatures/en-attente-revision`). |
| GET | `/candidatures/{id}` | Enseignant propriétaire, ou A+ de l'établissement du poste | UC-04 | Lecture, inclut le détail des notes par document |
| POST | `/candidatures/{id}/contestation` | Enseignant candidat | UC-04b | Fenêtre de 5 jours **ouvrés** (lundi-vendredi) après la candidature, uniquement si `statut=rejetee` |
| POST | `/contestations/{id}/decision` | A+ | UC-04b | `acceptee` / `rejetee`, motif obligatoire si rejet ; acceptée → candidature repasse `en_evaluation` |
| POST | `/candidatures/{id}/contrat` | A+ | UC-05 | Crée le contrat en attente de signature (syllabus) ; nécessite `statut=en_evaluation` avec un score calculé |
| POST | `/contrats/{id}/signer` | Enseignant titulaire | UC-05 | `multipart/form-data`, champ `signature_image` : tracé dessiné au doigt/stylet sur un canvas côté client, exporté en PNG. Signature électronique **simple** (Art. 284-285), pas qualifiée — décision définitive de l'utilisateur, voir ADR-004. Stockée via LuluFiles. |
| POST | `/contrats/{id}/reconduction` | A+ | UC-05b | Fenêtre de 30 jours avant `date_fin` ; crée un nouveau contrat en attente de signature |
| GET | `/candidatures/en-attente-revision` | A+ | UC-04 | Écran de révision manuelle : candidatures avec au moins un document en échec de notation IA |
| POST | `/documents-candidature/{id}/noter-manuellement` | A+ | UC-04 | Note manuelle (synchrone), puis recalcule automatiquement le score/statut de la candidature |
| GET | `/documents-candidature/{id}/lien` | Enseignant propriétaire, ou A+ de l'établissement du poste | UC-04 | **Ajouté a posteriori (audit frontend, 2026-09-25)** : lien signé LuluFiles vers le document lui-même — `note_ia` seule ne rendait pas l'écran de révision manuelle réellement utilisable. |
| GET | `/contrats/{id}/lien-signature` | Enseignant titulaire, ou A+ de l'établissement | UC-05 | **Ajouté a posteriori** : lien signé vers l'image de signature déposée par `POST /contrats/{id}/signer`, jusque-là jamais consultable. |

## Pédagogie

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/classes/{id}/cours` | Enseignant rattaché (contrat `signe` avec l'établissement de la classe) | UC-06 | `multipart/form-data` (titre, chapitre, format, contenu_texte ou fichier). 50 Mo max, upload vers LuluFiles si fichier fourni |
| GET | `/classes/{id}/cours` | Élève inscrit (`inscription validee`), Enseignant rattaché, A+ | UC-06 | Lecture, inclut désormais `contenu_texte` (**corrigé a posteriori, audit frontend 2026-09-25** : absent du premier jet, rendait un cours de format texte illisible par l'élève) |
| GET | `/cours/{id}/lien-fichier` | Élève inscrit, Enseignant rattaché | UC-06 | **Ajouté a posteriori** : lien signé LuluFiles pour un cours pdf/audio/vidéo — `lulufiles_file_id` était stocké mais jamais transformé en lien consultable (`LuluFilesClient.get_signed_link` n'était appelé nulle part) |
| GET | `/cours/{id}/quiz` | tout utilisateur authentifié (élève inscrit vérifié) | UC-07 | Liste les quiz du cours |
| POST | `/cours/{id}/quiz` | Enseignant propriétaire du cours | UC-07 | Questions **générées par FreeLLM** (QCM à 4 choix) à partir de `cours.contenu_texte` (obligatoire, sinon 422) ; seuil de réussite configurable, défaut 80% |
| GET | `/quiz/{id}` | Élève inscrit | UC-07 | Questions sans la bonne réponse (jamais exposée avant la tentative) |
| POST | `/quiz/{id}/tentatives` | Élève inscrit | UC-07 | `reponses: [index, ...]`, une par question, dans l'ordre. Tentatives illimitées ; score = % de bonnes réponses |
| GET | `/quiz/{id}/mes-tentatives` | Élève inscrit | UC-07 | Historique des tentatives de l'élève courant sur ce quiz, plus récente d'abord |

## Devoirs, évaluations, bulletins

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| GET | `/classes/{id}/devoirs` | Élève inscrit, Enseignant rattaché, A+ | UC-08 | Liste les devoirs de la classe |
| POST | `/classes/{id}/devoirs` | Enseignant rattaché | UC-08 | Formulaire : `matiere`, `bareme: rigide|flexible`, `questions: [{enonce, bareme_reponse, points_max}, ...]` |
| GET | `/devoirs/{id}/ma-soumission` | Élève | UC-08 | La soumission de l'élève courant pour ce devoir (404 si pas encore soumis) |
| POST | `/devoirs/{id}/soumissions` | Élève inscrit | UC-08 | `reponses: [{question_id, texte_reponse}, ...]`, une par question exactement. Rejetée (409) si la date limite est dépassée. Correction **automatique par FreeLLM**, exécutée **en arrière-plan** (`BackgroundTasks`, un appel réseau par question — pas de SLA, ADR-002) : la réponse renvoie `statut=en_correction`, à relire via `GET /soumissions/{id}` une fois le traitement terminé (rigide = tout ou rien, flexible = crédit partiel) ; en cas d'échec, `statut=echec_correction` et la soumission attend une révision manuelle |
| GET | `/soumissions/{id}` | Élève propriétaire, Enseignant du devoir, A+ | UC-08 | Permet de suivre l'avancement de la correction en arrière-plan |
| GET | `/devoirs/{id}/soumissions-a-revoir` | Enseignant propriétaire | UC-08 | Écran de révision manuelle : soumissions en `echec_correction` |
| GET | `/devoirs/{id}/questions-bareme` | Enseignant propriétaire | UC-08 | **Ajouté a posteriori (audit frontend, 2026-09-25)** : expose `bareme_reponse` par question pour l'écran de révision manuelle — jamais sur `DevoirOut`/`GET /devoirs/{id}`, qui restent accessibles à l'Élève avant sa réponse (l'y exposer aurait révélé la réponse attendue). |
| POST | `/soumissions/{id}/corriger` | Enseignant propriétaire du devoir | UC-08 | `reponses: [{question_id, points_obtenus}, ...]` — sert de filet de secours (échec IA) et de surcharge possible d'une correction déjà faite |
| GET | `/eleves/{id}/bulletins?classe_id=&periode=` | Élève, Tuteur, Enseignant rattaché, A+ | UC-09 | Calcule et enregistre la **moyenne pondérée** : chaque devoir est normalisé sur 100 puis pondéré par le coefficient (niveau, matière) du référentiel validé en vigueur (défaut 1.0 si aucun référentiel ne couvre la matière). Un devoir compte dès qu'il est corrigé, même avant son échéance formelle ; sans soumission, il ne compte comme 0 qu'une fois l'échéance passée |
| POST | `/bulletins/{id}/valider-passage` | Enseignant | UC-09 | Décision lourde (passage/redoublement/diplôme) toujours humaine, jamais déduite du seul calcul |
| GET | `/referentiels-coefficients` | A++, A+ | UC-09 | Liste tous les référentiels (dont les propositions en attente) — sans elle, aucune gouvernance possible sans déjà connaître les id |
| POST | `/referentiels-coefficients` | A++ | UC-09 | Référentiel national, `statut=valide` directement |
| POST | `/referentiels-coefficients/{id}/proposition` | A+ | UC-09 | Crée une proposition (`statut=proposition_en_attente`) liée au référentiel visé |
| POST | `/referentiels-coefficients/{id}/valider` | A++ | UC-09 | Seule action qui rend une proposition effective ; remplace l'ancien référentiel |

## Actes académiques

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/etablissements/{id}/types-actes` | A+ | UC-10 | Catalogue configurable : nom, prix, pièces requises (texte libre), condition d'éligibilité optionnelle |
| GET | `/etablissements/{id}/types-actes` | tout utilisateur authentifié concerné | UC-10 | Lecture du catalogue |
| GET | `/mes-demandes-actes` | Élève, Tuteur | UC-10 | Historique des demandes/réclamations de l'élève courant (ou de tous les enfants du tuteur courant), plus récentes d'abord |
| GET | `/etablissements/{id}/demandes-actes` | A+ | UC-10 | Demandes/réclamations (hors `soumise`, pas encore payées) des élèves de l'établissement, à traiter |
| POST | `/demandes-actes` | Élève (pour lui-même) ou Tuteur (avec `eleve_utilisateur_id`, doit être son enfant) | UC-10 | `est_reclamation: true` (gratuite, `reference_evaluation` obligatoire) **ou** `type_acte_id` (payant si `prix>0`, sinon `en_traitement` immédiat) |
| GET | `/demandes-actes/{id}` | Élève propriétaire, son Tuteur, A+ de l'établissement courant de l'élève | UC-10 | Lecture |
| POST | `/demandes-actes/{id}/traiter` | A+ | UC-10 | Accepte ou rejette (motif obligatoire) ; refusé (409) tant que le paiement n'est pas confirmé pour un acte payant |
| POST | `/demandes-actes/{id}/paiement/amorcer` | Élève ou Tuteur propriétaire | UC-10 | `transaction_id` : associe une transaction Kkiapay (obtenue côté client via le widget) à la demande, avant confirmation par le webhook |
| POST | `/paiements/webhook/kkiapay` | **public, URL unique pour tout le compte** (pas par demande) | UC-10 | Configuré une seule fois dans le tableau de bord Kkiapay (Clés API → Webhook). Vérifie l'en-tête `x-kkiapay-secret` contre `KKIAPAY_SECRET` ; sur `transaction.success`, retrouve la demande par `kkiapay_transaction_id` et confirme le paiement |

## Hors contrat pour l'instant

Pas d'endpoint pour la vérification du casier judiciaire (UC-04) : accès restreint à des personnes désignées, modélisé en dehors de l'API REST standard (interface d'administration séparée, à définir à l'étape 4 avec les mêmes contraintes d'accès que `VerificationCasierJudiciaire`).
