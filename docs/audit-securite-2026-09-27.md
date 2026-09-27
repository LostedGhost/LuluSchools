# Audit de sécurité et de fiabilité — 27 septembre 2026

Branche : `audit/securite-approfondie` (créée depuis `main` @ `3401eaa`).

## 1. Méthode

- Lecture intégrale des 21 routeurs backend (≈ 9 400 lignes) et du socle `app/core`, avec
  inventaire automatique des 243 endpoints et de leur dépendance d'authentification.
- Revue ciblée du frontend : stockage des jetons, intercepteur HTTP, puits XSS, secrets du bundle.
- Recherche de secrets dans tout l'historique git.
- Vérifications exécutées : suite pytest complète (SQLite **et** PostgreSQL réel), migration
  `0016` en montée/descente/remontée sur PostgreSQL, `alembic check`, `tsc -b`, `vite build`,
  `oxlint`, et parcours manuels en navigateur contre un backend réel (base jetable, services
  externes simulés).

## 2. Constats et correctifs

Gravité : **C** critique · **H** haute · **M** moyenne · **B** basse.

### Authentification et sessions

| # | Grav. | Constat | Correctif |
|---|---|---|---|
| 1 | H | Aucun renvoi d'OTP : un code expiré (10 min) ou épuisé (5 essais) bloquait le compte à vie (réinscription = 409). | `POST /auth/otp/renvoyer` (réponse générique), bouton « Renvoyer un nouveau code ». |
| 2 | H | Aucun parcours « mot de passe oublié ». | `POST /auth/mot-de-passe-oublie` (+ `/confirmer`) ; code envoyé au tuteur pour un compte élève (connexion par matricule). Page dédiée. |
| 3 | M | Aucune limitation de débit : force brute du mot de passe, spam d'e-mails Brevo. | Limiteur en mémoire (login par identifiant et par IP, OTP, inscription, renvoi, oubli, changement de mot de passe). |
| 4 | M | Un compte suspendu obtenait encore des jetons (login, refresh), accédait à `/me`, à la WebSocket live et à ~10 endpoints métier (`get_current_user`). | Suspension appliquée partout ; endpoints métier sur `get_current_active_user`. |
| 5 | M | Changer son mot de passe ne fermait pas les autres sessions (refresh 7 jours). | Marqueur de session dans le refresh token, révoqué à chaque changement/réinitialisation ; `change-password` renvoie une paire neuve. |
| 6 | M | Prénom saisi injecté tel quel dans le HTML des e-mails : hameçonnage depuis l'expéditeur officiel. | Échappement HTML de toutes les données interpolées. |
| 7 | B | Mot de passe sans borne haute (DoS argon2), énumération par timing au login, OTP comparé par `!=`, e-mail sensible à la casse. | Borne 128, vérification factice, `compare_digest`, identifiant normalisé. |
| 8 | B | `JWT_SECRET_KEY=change-me` par défaut sans garde. | Refus de démarrer en production sans secrets JWT/Kkiapay/casier valides. |

### Autorisations (IDOR) et intégrité des données

| # | Grav. | Constat | Correctif |
|---|---|---|---|
| 9 | H | Cours, liens de fichiers et quiz lisibles par tout tuteur/enseignant/A+ de n'importe quel établissement ; cours masqués par le Ministère toujours téléchargeables par l'élève. | Portée par rôle (élève inscrit, tuteur d'un enfant inscrit, enseignant affecté, A+ de l'établissement) ; contenu masqué → 404 pour élève/tuteur. |
| 10 | H | Un enseignant/A+ pouvait générer **et enregistrer** un bulletin pour n'importe quel élève du pays, qui remontait dans son dossier scolaire national. | Élève obligatoirement inscrit dans la classe ; bulletin figé après délibération du conseil. |
| 11 | H | Actes : un élève pouvait choisir le type d'acte (éventuellement gratuit) d'un autre établissement et contourner les frais. | Le type d'acte doit appartenir à l'établissement de l'élève ; décision limitée à accepter/rejeter. |
| 12 | H | Réinscription : la validation recréait un compte et un matricule, orphelinant le compte existant ; un tuteur ne pouvait que dupliquer son enfant. | Compte et matricule conservés ; enfant existant retrouvé ; doublons d'inscription refusés. |
| 13 | H | Un élève de moins de 16 ans pouvait cocher lui-même le consentement parental (Art. 446). | Seul le tuteur peut consentir. |
| 14 | M | Rejet possible d'une inscription déjà validée ; inscription dans un établissement suspendu. | Statuts contrôlés. |
| 15 | M | Messagerie : un enseignant sous contrat lisait les groupes de **toutes** les classes de l'établissement. | Limité aux classes affectées. |

### Recrutement et casier judiciaire (Art. 395)

| # | Grav. | Constat | Correctif |
|---|---|---|---|
| 16 | H | Le casier était chiffré puis conservé indéfiniment : aucun écran de vérification, aucun verdict, aucune purge (la rétention de 30 jours n'était pas appliquée). | Consultation réservée à l'A+ recruteur (journalisée, `no-store`), verdict conforme/non conforme qui purge le contenu, purge automatique à 30 jours (tâche planifiée en production), contrat subordonné à un casier conforme, panneau dédié côté A+. |
| 17 | **C** | `GET /candidatures/en-attente-revision` faisait un `DISTINCT` sur une colonne `json` : **erreur PostgreSQL systématique, tout l'écran Recrutement de l'A+ était inutilisable en production** (invisible sous SQLite). | Sous-requête `IN` ; test de non-régression ; suite de tests désormais exécutable sur PostgreSQL. |
| 18 | M | Candidature rejetée sous le seuil → score jamais calculé → une contestation **acceptée** ne pouvait jamais aboutir à un contrat. Contestations multiples et décisions modifiables ; délai compté depuis le dépôt et non le rejet. | Score toujours calculé, une contestation par candidature, décision définitive, délai depuis `rejetee_le`. |
| 19 | M | Candidatures en double ; plusieurs contrats sur un poste pourvu. | Refusés. |

### Paiements, séquestre et billetterie

| # | Grav. | Constat | Correctif |
|---|---|---|---|
| 20 | H | Validation tacite jamais appliquée aux files de reversement : un prestataire (micro-job) ou un vendeur (marketplace) dont le client restait silencieux **n'était jamais payé** ; l'A+ devait saisir les ID de transaction à la main. | Validation tacite appliquée à la lecture des files ; nouvelle file A+ « vendeurs à payer ». |
| 21 | M | Places réservées sans paiement jamais libérées : quelques comptes pouvaient bloquer une ligne de bus, un service de cantine, un événement ou toutes les annonces. | Place impayée retenue 30 min, un ticket par personne et par date, 3 réservations marketplace impayées max, verrou anti double réservation. |
| 22 | M | Ticket utilisable n'importe quel jour ; achat pour une date passée. | Validation le jour même (heure du Bénin), achat futur uniquement. |
| — | OK | Webhook Kkiapay : secret comparé en temps constant, montant vérifié, validation exigeant `paiement_confirme`. | — |

### Robustesse

| # | Grav. | Constat | Correctif |
|---|---|---|---|
| 23 | H | 7 endpoints `async def` exécutaient DB + upload LuluFiles synchrones (jusqu'à 120 s) : **toute l'API gelait** pendant un téléversement (un seul worker). | Endpoints synchrones (pool de threads). |
| 24 | M | Uploads lus entièrement en mémoire, sans type ni taille (casier, CV, signature, photos) — 512 Mo de RAM sur Render. | Lecture bornée par blocs + liste blanche de types, sur tous les téléversements. |
| 25 | M | Client LLM sans timeout (SDK : 10 min × 3) ; historique El Professor illimité (une session longue dépassait la fenêtre de contexte et devenait inutilisable) ; réponse d'élève concaténée aux consignes de correction (injection « donne-moi 20/20 »). | Timeout 60 s, historique plafonné, réponse isolée comme donnée. |
| 26 | M | Violations de contraintes SQL → 500. | 409/422 explicites. |
| 27 | M | Une capture de tableau en échec empêchait de terminer la session live ; traits illimités. | Capture best-effort, traits bornés, tableau figé après la session. |
| 28 | M | Frontend : un 401 sur `/auth/*` (mauvais mot de passe, code OTP erroné) redirigeait vers `/connexion`, effaçant l'erreur et éjectant l'utilisateur du parcours d'inscription. | Intercepteur ignoré pour `/auth/*`. |
| 29 | B | `alembic/env.py` n'importait pas les modèles marketplace, audit et coffre-fort : un `--autogenerate` proposait de **supprimer ces tables**. | Imports ajoutés. |
| 30 | B | Liens de visite virtuelle sans validation de schéma. | `https://` uniquement. |
| 31 | B | Aucun en-tête de sécurité sur le frontend. | `nosniff`, anti-framing, HSTS, `Permissions-Policy` (Vercel et Netlify). |

## 3. Vérifications

- Backend : **282 tests** (246 existants + 36 nouveaux : `test_securite_auth.py`,
  `test_securite_acces.py`), au vert sous SQLite. Mode PostgreSQL (`LULU_TEST_DATABASE_URL`) :
  premiers modules au vert, exécution complète interrompue par la saturation du disque C: de la
  machine de développement (voir § 4) — à rejouer (idéalement en CI).
- Migration `0016_durcissement_securite` : montée, descente, remontée vérifiées sur PostgreSQL.
- Frontend : `tsc -b`, `vite build`, `oxlint` (0 erreur).
- Navigateur, contre un backend réel : erreur de connexion affichée sur place ; mot de passe
  oublié de bout en bout ; code OTP erroné puis renvoi puis validation ; panneau casier
  (consultation, verdict conforme, apparition du formulaire de contrat) ; file « vendeurs à
  payer » et reversement.

## 4. Actions requises hors code

0. **Poste de développement** : le disque C: est plein (0 Go libre) ; le service
   `postgresql-x64-18` s'est arrêté en pleine récupération (« No space left on device »).
   Libérer de l'espace puis redémarrer le service (il terminera seul sa récupération). Les bases
   jetables créées pour cet audit (`luluschools_audit`, `luluschools_tests`) peuvent ensuite
   être supprimées.
1. **Rotation du mot de passe PostgreSQL** exposé dans l'historique git (`render.yaml`,
   commit antérieur) si ce n'est pas déjà fait — voir `docs/deploiement-render-vercel.md`.
   Le purger de l'historique si le dépôt est public.
2. **Déploiement** : `alembic upgrade head` applique `0016` au démarrage (déjà dans
   `startCommand`). Vérifier que `JWT_SECRET_KEY`, `KKIAPAY_SECRET` et
   `CASIER_JUDICIAIRE_ENCRYPTION_KEY` sont définis sur Render : le service refuse
   désormais de démarrer sans eux.
3. **Casiers déjà déposés** : leur échéance de purge est vide ; la tâche planifiée ne les purge
   qu'après verdict. Recommandé : rendre un verdict sur chaque candidature en cours.
4. **Contrats en attente** : une candidature ne peut plus recevoir de contrat sans verdict
   « conforme » sur le casier — informer les A+.

## 5. Risques résiduels (hors périmètre de cette branche)

- **Rattachement transaction ↔ ressource** : `…/paiement/amorcer` accepte l'identifiant de
  transaction fourni par le client, sans vérification côté Kkiapay. Le montant est contrôlé au
  webhook, mais un identifiant de transaction intercepté pourrait être rattaché à une autre
  ressource de même prix. Durcissement proposé : transmettre l'ID de ressource au widget
  (`data`) et le contrôler dans le webhook.
- **Limiteur en mémoire** : valable pour un seul worker (configuration actuelle) ; à déplacer
  vers un stockage partagé en cas de mise à l'échelle horizontale.
- **Jetons en `localStorage`** : exposés en cas de XSS (aucun puits XSS trouvé ; React échappe
  par défaut). Une CSP stricte reste à définir après inventaire du widget Kkiapay et des
  ressources de la landing page.
- **Dérive cosmétique de schéma** : deux types enum PostgreSQL nommés différemment des modèles
  et trois contraintes d'unicité exprimées en contrainte plutôt qu'en index — sans effet à
  l'exécution (vérifié), à aligner lors d'une prochaine migration.
- **Pagination** : plusieurs listes (messages d'une conversation, signalements) restent non
  paginées.
- **Règles produit à arbitrer** (non modifiées, faute de décision métier) : un élève peut
  ouvrir une conversation privée avec n'importe quel autre élève de la plateforme (tous
  établissements confondus) ; un A+ peut désigner comme contrôleur n'importe quel compte, pas
  seulement ceux proposés par la recherche (enseignants sous contrat, admins).
- **CI** : ajouter à `backend-ci.yml` une seconde exécution de `pytest` avec
  `LULU_TEST_DATABASE_URL` pointant sur le service PostgreSQL déjà présent (non fait ici :
  modification de pipeline laissée à votre validation).
