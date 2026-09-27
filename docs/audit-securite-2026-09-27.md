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

### Seconde passe (même jour) : risques résiduels et points mineurs

| # | Grav. | Constat | Correctif |
|---|---|---|---|
| 32 | H | Rattachement paiement ↔ ressource par un identifiant de transaction fourni par le navigateur : un identifiant intercepté pouvait être rattaché à une autre ressource de même prix. | Le widget transmet `partnerId` = `<type>:<id>` (champ documenté par Kkiapay, renvoyé dans le webhook) : la ressource désignée par le payeur fait foi, un rattachement concurrent est défait. Repli sur l'ancien rattachement pour les paiements déjà amorcés. |
| 33 | H | Frontend : les écouteurs de succès Kkiapay s'empilaient à chaque ouverture du widget ; un paiement réussi était rattaché à toutes les ressources ouvertes auparavant. | Un seul écouteur, routé vers le paiement en cours. |
| 34 | M | Limitation de débit en mémoire (un seul worker). | Compteurs en base (`tentatives_limitees`). |
| 35 | M | Aucune Content-Security-Policy (jetons en `localStorage` exposés à toute injection de script). | CSP stricte (Vercel, Netlify, `vite preview`), sources inventoriées ; vérifiée sur le build de production. |
| 36 | B | Dérive de schéma (types enum, unicité). | Migration `0017` ; `alembic check` : aucune dérive. |
| 37 | M | Messages d'une conversation et signalements non paginés ; liste des signalements lisant ceux de tout le pays. | Pagination par curseur (+ bouton « charger les précédents ») ; requête jointe, 200 max. |
| 38 | M | Devoir masqué accessible par lien direct et soumettable par l'élève/le tuteur. | 404 pour eux. |
| 39 | M | Élève désinscrit conservant l'accès à une session live déjà rejointe. | Inscription validée exigée à chaque accès. |
| 40 | M | Tickets transport/cantine achetables par un élève d'un autre établissement. | Réservés aux élèves de l'établissement. |
| 41 | M | Inscription et vérification OTP révélaient l'existence d'un compte. | Réponse identique ; le propriétaire de l'adresse est prévenu par e-mail. |
| 42 | B | Photos publiques d'un établissement suspendu ; file de révision vide pour l'A++ ; signalements en double ; listes à requêtes multiples. | Corrigés. |
| 43 | — | **Arbitrages du 2026-09-27** : messagerie privée élève ↔ élève possible entre tous les établissements ; contrôleur désignable parmi tous les comptes. | Limitée au même établissement ; contrôleur choisi parmi les enseignants sous contrat et les admins de l'établissement. |

## 3. Vérifications

- Backend : **295 tests** (246 existants + 49 nouveaux : `test_securite_auth.py`,
  `test_securite_acces.py`, `test_securite_complements.py`), **au vert sous SQLite ET sous
  PostgreSQL** (`LULU_TEST_DATABASE_URL`, désormais exécuté en CI).
- Migrations `0016` et `0017` : montée, descente, remontée vérifiées sur PostgreSQL ;
  `alembic check` sans aucune dérive.
- Frontend : `tsc -b`, `vite build`, `oxlint` (0 erreur).
- Navigateur, contre un backend réel : erreur de connexion affichée sur place ; mot de passe
  oublié de bout en bout ; code OTP erroné puis renvoi puis validation ; panneau casier
  (consultation, verdict conforme, apparition du formulaire de contrat) ; file « vendeurs à
  payer » et reversement. CSP vérifiée sur le build de production : rendu de la landing
  page, chargement du script Kkiapay, tuiles OpenStreetMap et photos Pexels autorisés,
  domaine non listé bloqué, aucune violation en console.

### 3.1 Parcours complet de tous les rôles (build de production + PostgreSQL réel)

Frontend servi par `vite preview` (build de production, CSP active), backend réel sur une
base PostgreSQL neuve migrée par Alembic, jeu de données créé par l'API. Seuls l'e-mail, le
stockage de fichiers et le LLM étaient simulés ; le widget Kkiapay était simulé côté
navigateur et son webhook rejoué avec le `partnerId` attendu. Chaque écran de chaque rôle
a été ouvert : **aucune erreur API inattendue, aucune erreur JavaScript, aucune violation CSP**.

| Rôle | Actions exercées de bout en bout |
|------|----------------------------------|
| A++ | Tableau de bord, établissements, suspension puis réactivation d'un compte (journal d'audit, connexion refusée pendant la suspension), reversement micro-job. |
| A+ lycée / université | Verdict casier + contrat, validation d'inscription, acceptation d'acte et remise du document, reversement vendeur marketplace. |
| Enseignant | Signature de contrat par tracé, publication de cours, quiz généré par IA, devoir, note de vie scolaire, contrôle de tickets et billets (double validation refusée), session live (WebSocket sous CSP, chat). |
| Tuteur | Consentement, achat et paiement de ticket, message à l'enfant, billet d'événement payé. |
| Élève | Quiz (100/100), devoir corrigé automatiquement, acte payé, session live, messagerie, groupe de classe. |
| Étudiant | Marketplace (réservation, paiement, remise, confirmation), micro-job (publication, paiement, acceptation, fin, validation). |

Défauts trouvés et corrigés pendant ce parcours :

| # | Gravité | Défaut | Correctif |
|---|---------|--------|-----------|
| 44 | É | Aucun moyen pour un élève ou un étudiant de renseigner son numéro Mobile Money : le reversement des ventes marketplace et des micro-jobs était impossible. | `PATCH /me` (numéro validé) + encart « Numéro Mobile Money » sur les pages Marketplace et Micro-jobs. |
| 45 | M | Menu de l'élève (non étudiant) affichant Micro-jobs et Marketplace, qui lui répondent 403. | Entrées réservées aux étudiants. |
| 46 | M | Ticket non payé affiché « Valide » avec un bouton « Rembourser ». | « Paiement en attente » / « Payé — à présenter » ; bouton « Annuler » tant qu'il n'est pas payé. |
| 47 | B | Bulletin : erreur rouge en début de période au lieu d'un état vide ; note de devoir affichée sur 20 quel que soit le barème ; « / 100 » doublé sur les scores de quiz et de bulletin. | Corrigés. |

Points mineurs non corrigés (cosmétiques) : le message de succès du contrôle d'accès reste
affiché jusqu'au scan suivant ; le panneau de suspension A++ s'ouvre sous le tableau.

## 4. Actions requises hors code

0. **Poste de développement** : le disque C: est plein (0 Go libre) ; le service
   `postgresql-x64-18` s'est arrêté en pleine récupération (« No space left on device »).
   Libérer de l'espace puis redémarrer le service (il terminera seul sa récupération). Les bases
   jetables créées pour cet audit (`luluschools_audit`, `luluschools_tests`) peuvent ensuite
   être supprimées.
1. **Rotation du mot de passe PostgreSQL** exposé dans l'historique git (`render.yaml`,
   commit antérieur) si ce n'est pas déjà fait — voir `docs/deploiement-render-vercel.md`.
   Le purger de l'historique si le dépôt est public.
2. **Déploiement** : `alembic upgrade head` applique `0016` et `0017` au démarrage (déjà dans
   `startCommand`). Vérifier que `JWT_SECRET_KEY`, `KKIAPAY_SECRET` et
   `CASIER_JUDICIAIRE_ENCRYPTION_KEY` sont définis sur Render : le service refuse
   désormais de démarrer sans eux.
3. **Casiers déjà déposés** : leur échéance de purge est vide ; la tâche planifiée ne les purge
   qu'après verdict. Recommandé : rendre un verdict sur chaque candidature en cours.
4. **Contrats en attente** : une candidature ne peut plus recevoir de contrat sans verdict
   « conforme » sur le casier — informer les A+.

## 5. Risques résiduels

- **Jetons en `localStorage`** : désormais protégés par la CSP ; un passage du refresh token
  en cookie `HttpOnly` réduirait encore l'exposition, mais demande un proxy même-origine
  pour l'API (déjà le cas via Vercel/Netlify) et une refonte du flux de rafraîchissement.
- **Paiements amorcés avant le déploiement** : ils restent confirmés par l'ancien
  rattachement (sans `partnerId`) ; le risque disparaît de lui-même avec eux.
- **Paiement Kkiapay réel non rejoué** : le rattachement par `partnerId` est vérifié contre la
  documentation et le SDK, et simulé de bout en bout ; un paiement en mode *sandbox* sur
  l'environnement déployé reste la seule preuve définitive.
- **`style-src 'unsafe-inline'`** dans la CSP : nécessaire aux styles injectés par Leaflet et
  le widget Kkiapay ; le risque (injection de style, pas de script) est faible.
