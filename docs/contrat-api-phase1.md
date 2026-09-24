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
| POST | `/etablissements/{id}/classes` | A+ | UC-02, UC-03 | Définit niveau, capacité, politique de dépassement |
| GET | `/etablissements/{id}/classes` | tout utilisateur authentifié | — | Lecture |

## Inscriptions

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/inscriptions` | Tuteur | UC-02 | Statut initial `soumise` ou `en_attente_consentement_parental` selon l'âge (peut être court-circuité par `consentement_parental_donne: true` à la soumission). **Limitation Phase 1** : l'auto-inscription directe par un élève ≥16 ans sans tuteur n'est pas implémentée (nécessiterait un flux de compte dédié, symétrique à UC-01) — seul un tuteur peut soumettre pour l'instant. |
| POST | `/inscriptions/{id}/consentement-parental` | Tuteur rattaché | UC-02 | Débloque une inscription en attente de consentement |
| POST | `/inscriptions/{id}/valider` | A+ (de l'établissement de la classe) | UC-02, UC-03 | Refusé (409) si consentement manquant ou classe complète (capacité atteinte, compte les inscriptions déjà `validee`). Génère le matricule (`BJ-{code_etab}-{annee}-{sequence}`) et le compte élève (mot de passe temporaire envoyé au tuteur par e-mail). |
| POST | `/inscriptions/{id}/rejeter` | A+ | UC-02 | Motif obligatoire |
| GET | `/inscriptions/{id}` | Tuteur rattaché, ou A+ de l'établissement de la classe | UC-02 | Lecture (contrôle d'accès vérifié, pas seulement l'authentification — anti-IDOR) |

## Recrutement et contrats

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/etablissements/{id}/postes` | A+ | UC-04 | Définit les critères par type de document (coefficient, seuil minimal) |
| GET | `/postes/{id}` | tout utilisateur authentifié | UC-04 | Lecture |
| POST | `/postes/{id}/candidatures` | Enseignant | UC-04 | `multipart/form-data` : `types[]` + `fichiers[]` (un par critère du poste, exactement) + `casier_judiciaire` à part. Upload vers LuluFiles puis notation FreeLLM **synchrone** (pas encore en tâche de fond) pour chaque document scoré ; le casier judiciaire est stocké localement, jamais sur LuluFiles (Art. 395). Si un document échoue à être noté (FreeLLM indisponible), la candidature reste `en_evaluation` sans score, en attente d'une révision manuelle — **l'endpoint de revue manuelle n'est pas encore construit**. |
| GET | `/candidatures/{id}` | Enseignant propriétaire, ou A+ de l'établissement du poste | UC-04 | Lecture, inclut le détail des notes par document |
| POST | `/candidatures/{id}/contestation` | Enseignant candidat | UC-04b | Fenêtre de 5 jours (calendaires en implémentation actuelle — la spec dit "ouvrés", simplification à corriger) après la candidature, uniquement si `statut=rejetee` |
| POST | `/contestations/{id}/decision` | A+ | UC-04b | `acceptee` / `rejetee`, motif obligatoire si rejet ; acceptée → candidature repasse `en_evaluation` |
| POST | `/candidatures/{id}/contrat` | A+ | UC-05 | Crée le contrat en attente de signature (syllabus) ; nécessite `statut=en_evaluation` avec un score calculé |
| POST | `/contrats/{id}/signer` | Enseignant titulaire | UC-05 | **Implémenté en signature simple (horodatage + hash + nom tapé vérifié), pas la signature qualifiée prévue pour la V1 — aucun prestataire de certification n'a été choisi (point ouvert)** |
| POST | `/contrats/{id}/reconduction` | A+ | UC-05b | **Non implémenté** (modèle de données `PropositionReconduction` posé, endpoint à écrire) |
| POST | `/referentiels-coefficients` | A++ | UC-09 | **Non implémenté** |
| POST | `/referentiels-coefficients/{id}/proposition` | A+ | UC-09 | **Non implémenté** |
| POST | `/referentiels-coefficients/{id}/valider` | A++ | UC-09 | **Non implémenté** |

## Pédagogie

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/classes/{id}/cours` | Enseignant rattaché (contrat `signe` avec l'établissement de la classe) | UC-06 | `multipart/form-data` (titre, chapitre, format, contenu_texte ou fichier). 50 Mo max, upload vers LuluFiles si fichier fourni |
| GET | `/classes/{id}/cours` | Élève inscrit (`inscription validee`), Enseignant rattaché, A+ | UC-06 | Lecture |
| POST | `/cours/{id}/quiz` | Enseignant propriétaire du cours | UC-07 | Seuil de réussite configurable, défaut 80% |
| POST | `/quiz/{id}/tentatives` | Élève inscrit | UC-07 | Tentatives illimitées. **Limitation** : pas de banque de questions/réponses (non spécifiée par un UC validé) — le score est fourni par l'appelant, pas encore calculé à partir de vraies réponses |

## Devoirs, évaluations, bulletins

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/classes/{id}/devoirs` | Enseignant rattaché | UC-08 | `bareme: rigide|flexible` |
| POST | `/devoirs/{id}/soumissions` | Élève inscrit | UC-08 | Rejetée (409) si la date limite est dépassée — pas de soumission tardive acceptée. L'absence de ligne de soumission compte pour 0 au calcul du bulletin (pas besoin de tâche planifiée) |
| POST | `/soumissions/{id}/corriger` | Enseignant propriétaire du devoir | UC-08 | Note manuelle dans les deux cas (barème rigide non auto-corrigé pour l'instant — pas de corrigé-type spécifié par un UC validé) |
| GET | `/eleves/{id}/bulletins?classe_id=&periode=` | Élève, Tuteur, Enseignant rattaché, A+ | UC-09 | Calcule et enregistre la moyenne (moyenne simple sur les devoirs clos et notés — **pas encore pondérée par les coefficients du référentiel**, à brancher) |
| POST | `/bulletins/{id}/valider-passage` | Enseignant | UC-09 | Décision lourde (passage/redoublement/diplôme) toujours humaine, jamais déduite du seul calcul |
| POST | `/referentiels-coefficients` | A++ | UC-09 | Référentiel national, `statut=valide` directement |
| POST | `/referentiels-coefficients/{id}/proposition` | A+ | UC-09 | Crée une proposition (`statut=proposition_en_attente`) liée au référentiel visé |
| POST | `/referentiels-coefficients/{id}/valider` | A++ | UC-09 | Seule action qui rend une proposition effective ; remplace l'ancien référentiel |

## Actes académiques

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/etablissements/{id}/types-actes` | A+ | UC-10 | Catalogue configurable : nom, prix, pièces requises (texte libre), condition d'éligibilité optionnelle |
| GET | `/etablissements/{id}/types-actes` | tout utilisateur authentifié concerné | UC-10 | Lecture du catalogue |
| POST | `/demandes-actes` | Élève | UC-10 | `est_reclamation: true` (gratuite, `reference_evaluation` obligatoire) **ou** `type_acte_id` (payant si `prix>0`, sinon `en_traitement` immédiat). **Limitation** : le tuteur ne peut pas soumettre au nom de l'élève pour l'instant |
| GET | `/demandes-actes/{id}` | Élève propriétaire, A+ de l'établissement courant de l'élève | UC-10 | Lecture |
| POST | `/demandes-actes/{id}/traiter` | A+ | UC-10 | Accepte ou rejette (motif obligatoire) ; refusé (409) tant que le paiement n'est pas confirmé pour un acte payant |
| POST | `/demandes-actes/{id}/paiement/webhook` | public | UC-10 | **L'intégration Kkiapay réelle (vérification de signature) n'est pas construite** — pose seulement la forme de la confirmation, à sécuriser avant mise en production |

## Hors contrat pour l'instant

Pas d'endpoint pour la vérification du casier judiciaire (UC-04) : accès restreint à des personnes désignées, modélisé en dehors de l'API REST standard (interface d'administration séparée, à définir à l'étape 4 avec les mêmes contraintes d'accès que `VerificationCasierJudiciaire`).
