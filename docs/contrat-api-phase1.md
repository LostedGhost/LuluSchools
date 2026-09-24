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
| POST | `/etablissements` | A++ | — | Création d'un établissement (EP/ES/UP), attribue le code établissement |
| GET | `/etablissements` / `/etablissements/{id}` | tout utilisateur authentifié | — | Lecture |
| POST | `/etablissements/{id}/classes` | A+ | UC-02, UC-03 | Définit niveau, capacité, politique de dépassement |
| GET | `/etablissements/{id}/classes` | tout utilisateur authentifié | — | Lecture |

## Inscriptions

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/inscriptions` | Tuteur, ou Élève ≥16 ans | UC-02 | Statut initial `soumise` ou `en_attente_consentement_parental` selon l'âge |
| POST | `/inscriptions/{id}/consentement-parental` | Tuteur rattaché | UC-02 | Débloque une inscription en attente de consentement |
| POST | `/inscriptions/{id}/valider` | A+ | UC-02, UC-03 | Génère le matricule (UC-03 est interne, pas d'endpoint dédié) |
| POST | `/inscriptions/{id}/rejeter` | A+ | UC-02 | Motif obligatoire |
| GET | `/inscriptions/{id}` / `/inscriptions?eleve_id=&etablissement_id=&statut=` | selon rattachement | UC-02 | Lecture |

## Recrutement et contrats

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/etablissements/{id}/postes` | A+ | UC-04 | Définit seuils/coefficients par type de document, capacité |
| GET | `/postes/{id}` | tout utilisateur authentifié | UC-04 | Lecture |
| POST | `/postes/{id}/candidatures` | Enseignant | UC-04 | Upload des documents ; déclenche la notation IA (FreeLLM, hors casier judiciaire) en tâche de fond |
| GET | `/candidatures/{id}` / `/candidatures?enseignant_id=&poste_id=&statut=` | selon rattachement | UC-04 | Lecture, inclut le détail des notes par document |
| POST | `/candidatures/{id}/contestation` | Enseignant candidat | UC-04b | Fenêtre de 5 jours ouvrés après notification du rejet |
| POST | `/contestations/{id}/decision` | A+ | UC-04b | `acceptee` / `rejetee`, motif obligatoire si rejet |
| POST | `/candidatures/{id}/contrat` | A+ | UC-05 | Crée le contrat en attente de signature (syllabus + rémunération) |
| POST | `/contrats/{id}/signer` | Enseignant titulaire | UC-05 | Signature électronique qualifiée (prestataire externe, cf. `choix-technique-phase1.md`) |
| POST | `/contrats/{id}/reconduction` | A+ | UC-05b | Crée un nouveau contrat en attente de signature, inclut `POST /contrats/{id}/signer` |
| POST | `/referentiels-coefficients` | A++ | UC-09 | Référentiel national initial |
| POST | `/referentiels-coefficients/{id}/proposition` | A+ | UC-09 | Proposition de mise à jour |
| POST | `/referentiels-coefficients/{id}/valider` | A++ | UC-09 | Seule action qui rend une proposition effective |

## Pédagogie

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/classes/{id}/cours` | Enseignant rattaché | UC-06 | Formats texte/PDF/audio, 50 Mo max par défaut |
| GET | `/cours/{id}` / `/classes/{id}/cours` | Élève inscrit, Enseignant rattaché | UC-06 | Lecture |
| POST | `/cours/{id}/quiz` | Enseignant | UC-07 | Seuil de réussite configurable, défaut 80% |
| POST | `/quiz/{id}/tentatives` | Élève inscrit | UC-07 | Tentatives illimitées, retourne résultat + déblocage du chapitre suivant |

## Devoirs, évaluations, bulletins

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/classes/{id}/devoirs` | Enseignant | UC-08 | `bareme: rigide|flexible`, non modifiable après première soumission |
| POST | `/devoirs/{id}/soumissions` | Élève inscrit | UC-08 | Verrouillage strict à l'échéance, absence → note 0 sans dérogation |
| POST | `/soumissions/{id}/corriger` | Enseignant | UC-08 | Automatique si barème rigide, manuel si flexible |
| GET | `/eleves/{id}/bulletins` / `/bulletins/{id}` | Élève, Tuteur, Enseignant rattaché | UC-09 | Calcul automatique de la moyenne |
| POST | `/bulletins/{id}/valider-passage` | Enseignant (conseil de classe) | UC-09 | Décision lourde (passage/redoublement/diplôme) toujours humaine |

## Actes académiques

| Méthode | Chemin | Rôle | UC | Notes |
|---|---|---|---|---|
| POST | `/demandes-actes` | Élève, Tuteur | UC-10 | `type: reclamation_note|delivrance_bulletin|delivrance_attestation|delivrance_diplome` |
| GET | `/demandes-actes/{id}` / `/demandes-actes?statut=&type=` | selon rattachement, A+ | UC-10 | Lecture |
| POST | `/demandes-actes/{id}/traiter` | A+ | UC-10 | Accepte (document/correction produite) ou rejette (motif obligatoire) |
| POST | `/demandes-actes/{id}/paiement/webhook` | public (signature Kkiapay vérifiée) | UC-10 | Confirmation de paiement pour les types payants uniquement |

## Hors contrat pour l'instant

Pas d'endpoint pour la vérification du casier judiciaire (UC-04) : accès restreint à des personnes désignées, modélisé en dehors de l'API REST standard (interface d'administration séparée, à définir à l'étape 4 avec les mêmes contraintes d'accès que `VerificationCasierJudiciaire`).
