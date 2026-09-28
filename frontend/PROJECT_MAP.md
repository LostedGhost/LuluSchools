# frontend/ — Project Map

## Stack
Vite + React 19 + TypeScript, Tailwind CSS v4 (`@tailwindcss/vite`, pas de `tailwind.config.js` — voir `vite.config.ts`), `react-router-dom` (routing), `axios` (client API), `three` (scène 3D de la landing page uniquement, chargée à la demande — voir ADR-009, ne jamais l'importer statiquement ailleurs). Pas de librairie de gestion de formulaire/état serveur (React Query, etc.) — le volume de la Phase 1 ne le justifie pas encore ; a réévaluer si la duplication de logique de fetch devient un problème réel.

Le serveur de dev proxy `/api` vers `http://127.0.0.1:8000` (backend local) — voir `vite.config.ts`. En production, le frontend et le backend seront servis derrière le même reverse proxy Nginx (ADR-001), donc `/api/v1/...` restera un chemin relatif valide sans changement de code.

## Design system
`src/index.css` porte l'intégralité des tokens visuels (couleurs, ombres, typographie, rayons) sous forme de variables CSS (`--primary`, `--reward`, `--action`, `--magic`, `--shadow-*`, `--font-*`...), en clair et en sombre (`@media (prefers-color-scheme: dark)` + `[data-theme]`, bascule pilotée par `AppLayout.tsx`/`ThemeProvider`, persistée dans `localStorage` sous `ls-theme`). Identité institutionnelle (État béninois, plateforme nationale de l'éducation) depuis ADR-007 : palette verte de marque + ambre/rouge/bleu strictement fonctionnels (plus de violet décoratif — `--magic` est aliasé sur les valeurs bleues de `--info`), ombres diffuses plutôt que portées dures, bordures fines (1–1.5px), typographie Rubik (titres/corps) + JetBrains Mono (données) + Itim (réservée au wordmark « Lulu·Schools », jamais en paragraphe). **Aucun emoji nulle part sur la plateforme** — toutes les icônes passent par `lucide-react` ; les props `icon` des composants partagés (`KPITile`, `EmptyState`, `QuestCard`, `AchievementToast`, `AIBadge`, médailles de `gamification.tsx`) sont typées `ReactNode`, jamais `string`, pour empêcher qu'un emoji soit réintroduit comme valeur par défaut.
- `src/components/Tilt3D.tsx` — carte à bascule 3D réactive au curseur (`rotateX`/`rotateY` calculés depuis la position de la souris, glare optionnel, respect de `prefers-reduced-motion`), utilisée sur la landing page.
- Gamification (XP, niveaux, séries, médailles) volontairement cantonnée aux écrans où elle a un sens pédagogique direct (tableau de bord élève, hero de la landing page) plutôt que déployée par défaut sur les tableaux de bord administratifs et les pages de gestion — voir ADR-007.
- Relief visuel du hero (`.dot-grid-bg`, `.hero-glow`, `.text-gradient` dans `index.css`) ajouté en réponse au retour « trop plat / générique » sur la première passe du design system institutionnel (ADR-007).
- **Scène 3D de la landing page (ADR-009)**, en réponse au retour utilisateur prenant explicitement la landing page de LuluFiles comme référence (étoiles animées + objet 3D flottant) :
  - `src/components/StarfieldScene.tsx` — champ d'étoiles Three.js/WebGL (technique copiée de LuluFiles, palette adaptée), **chargé à la demande** (`React.lazy` dans `LandingPage.tsx`) pour ne jamais alourdir le bundle des autres pages — vérifier que le build produit bien un chunk `StarfieldScene-*.js` séparé après toute modification touchant `three`.
  - `src/components/FloatingObjects3D.tsx` (`DiplomaCard`, `FloatingMedal`) — objets décoratifs en CSS `preserve-3d` (pas WebGL, cf. raisonnement LuluFiles cité dans ADR-009), classes dans `index.css` section « SCÈNE 3D ».
  - `src/hooks/useReducedMotion.ts` — utilisé par `StarfieldScene` (et réutilisable pour toute future animation lourde).
- **Vitrine → annuaire public (ADR-009)** : la landing page n'affiche plus qu'un teaser compact (bandeau + puces de noms, `vitrinePublique()` sur `GET /etablissements/vitrine-publique`) ; la liste complète est sur sa propre route publique `src/pages/EtablissementsAnnuairePage.tsx` (`/etablissements`, recherche + filtre par type + pagination, `annuairePublic()` sur `GET /etablissements/annuaire-public`). Ne jamais remettre la liste complète des établissements sur la landing page, même si elle est courte aujourd'hui — la plateforme a vocation nationale.
- **Photos d'établissement (ADR-009)** : `src/components/Carousel.tsx` (carrousel générique, dégrade sur 0/1 photo) utilisé dans les cartes de `EtablissementsAnnuairePage.tsx` (fetch par carte via `photosPubliques()`, jamais en masse). Upload/suppression réservés à l'A+ via `src/components/PhotosEtablissementManager.tsx`, monté dans `AdminEtabDashboard.tsx`.

## Arborescence
- `src/types/api.ts` — types TS miroir des schémas Pydantic du backend (contrat : `docs/contrat-api-phase1.md`). Tenu à jour manuellement, pas de génération automatique (OpenAPI codegen) pour l'instant. **Attention** : pour un type `str, enum.Enum` côté backend, la valeur JSON exposée est `.value` (ex. `PolitiqueDepassement.TIRAGE_SORT` → `"tirage_sort"`), pas le nom du membre Python — un frontend qui suppose le mauvais mapping échoue silencieusement à l'exécution (bug réel trouvé et corrigé pendant cette étape, voir plus bas).
- `src/api/` — un module par domaine backend (`auth.ts`, `etablissements.ts`, `inscriptions.ts`, `pedagogie.ts`, `evaluations.ts`, `evaluations_gouvernance.ts`, `actes.ts`, `recrutement.ts`), chacun exposant des fonctions typées autour de l'instance axios `client.ts`.
- `src/api/client.ts` — instance axios avec intercepteur d'auth (Bearer token depuis `localStorage`) et rafraîchissement automatique du token sur 401 (refresh token, un seul refresh en vol partagé entre requêtes concurrentes via `refreshEnCours`).
- `src/auth/AuthContext.tsx` — état d'authentification global (`utilisateur: MeOut | null`), `seConnecter`/`seDeconnecter`/`rafraichirUtilisateur`.
- `src/auth/RequireAuth.tsx` — garde de route : redirige vers `/connexion` si non authentifié, vers `/changer-mot-de-passe` si `mot_de_passe_temporaire=true` (bloque l'accès au reste de l'app tant que ce n'est pas fait, cohérent avec `get_current_active_user` côté backend), filtre par rôle (`roles` prop).
- `src/eleve/EleveProfileContext.tsx` — contexte séparé de `AuthContext` : charge `GET /eleves/me` une fois par montage de route élève (matricule, classe actuelle) ; toutes les pages élève en dépendent pour connaître leur `classe_id`.
- `src/admin/AdminEtabContext.tsx` — équivalent pour l'A+ : charge `GET /etablissements/mon-etablissement` (l'établissement administré n'est pas déductible de `GET /me`).
- `src/layout/AppLayout.tsx` — en-tête + navigation, adaptée au rôle courant (`navPourRole` couvre les 5 rôles : tuteur, élève, enseignant, admin_etablissement, admin_ministeriel).
- `src/components/ui.tsx` — kit d'UI minimal partagé (Card, boutons, champs, badges, bannière d'erreur) — pas de librairie de composants externe.
- `src/pages/admin/ATraiterPage.tsx` (+ `ATraiterEtablissementPage.tsx` pour l'A+) — boîte « À traiter » (premier élément du menu A+ et A++, `api/administration.ts`) : files d'attente de tous les modules, actions groupées (validation d'inscriptions, suggestions de l'IA, reconductions, affectations proposées, reversements par bénéficiaire, remboursements manuels), recrutement et litiges en un clic, réglage d'admission automatique. `ActesAdminPage.tsx` : choix de la délivrance automatique d'un type d'acte.
- `src/components/NumeroMobileMoney.tsx` — encart de saisie du numéro Mobile Money (`PATCH /me`), monté sur les pages Marketplace et Micro-jobs : sans numéro, aucun reversement possible. Le menu élève n'affiche ces deux modules qu'aux étudiants (`navPourRole(role, estEtudiant)` dans `AppLayout.tsx`).
- `src/components/KkiapayButton.tsx` — charge le script `https://cdn.kkiapay.me/k.js` à la demande et ouvre le widget Kkiapay (`openKkiapayWidget`/`addSuccessListener`/`addFailedListener`). Clé publique et mode sandbox lus depuis `VITE_KKIAPAY_PUBLIC_KEY`/`VITE_KKIAPAY_SANDBOX` (voir `.env.example`) — jamais la clé privée, qui reste backend-only.
- `src/components/SignatureCanvas.tsx` — capture un tracé au pointeur (souris/tactile) sur un `<canvas>`, exporté en PNG (`canvas.toBlob`) pour `POST /contrats/{id}/signer` (ADR-004, signature électronique simple).
- `src/pages/` — une page par écran, organisées par rôle (`tuteur/`, `eleve/`, `enseignant/`, `admin_etablissement/`, `admin_ministeriel/`) ou transverses (`LoginPage`, `SignupPage` (paramétrée par `role: "tuteur" | "enseignant"`, remplace l'ancienne `SignupTuteurPage`), `ChangePasswordPage`, `DashboardRedirect`).

## Parcours construits (étape 6) — les 5 rôles de la Phase 1
- **Tuteur** : `SignupPage role="tuteur"` (inscription + vérification OTP), `TuteurDashboard` (liste des enfants et statut via `GET /tuteurs/me/inscriptions`, don de consentement parental), `NouvelleInscriptionPage` (choix établissement → classe → formulaire enfant).
- **Élève** : `EleveDashboard`, `CoursListPage` + `QuizPage` (quiz généré par IA, tentatives illimitées, historique via `GET /quiz/{id}/mes-tentatives`), `DevoirsListPage` + `DevoirDetailPage` (soumission d'un devoir puis **suivi en direct de la correction IA en arrière-plan** — `statut=en_correction` affiché immédiatement, `setInterval` de 3s qui relit `GET /devoirs/{id}/ma-soumission` jusqu'à résolution, cohérent avec ADR-005), `BulletinPage` (sélecteur de trimestre), `ActesPage` (demande d'acte du catalogue ou réclamation, paiement Kkiapay pour les actes payants).
- **Enseignant** : `SignupPage role="enseignant"`, `PostesListPage` + `PostulerPage` (candidature multipart), `MesCandidaturesPage` (suivi + contestation), `MesContratsPage` (signature via `SignatureCanvas`), `MesCoursPage` (publication de cours, génération de quiz IA), `MesDevoirsPage` (création de devoir à questions dynamiques, révision manuelle des soumissions en `echec_correction` avec saisie des points par question — pas de crédit automatique).
- **A+ (admin établissement)** : `AdminEtabDashboard`, `ClassesPage` (création + liste), `InscriptionsAValiderPage` (valider/rejeter), `RecrutementPage` (ouvrir un poste, lister les candidatures d'un poste via `GET /postes/{id}/candidatures`, **créer le contrat** d'une candidature éligible, révision manuelle des documents en `echec_notation`), `ContestationsPage` (accepter/rejeter), `ActesAdminPage` (catalogue + traitement des demandes).
- **A++ (admin ministériel)** : `EtablissementsPage` (création d'établissement + provisionnement de son A+, réutilise le même flux d'e-mail temporaire que UC-01/UC-04), `ReferentielsPage` (fixer un référentiel national, valider une proposition d'A+ — pas de vue de proposition côté A+ pour l'instant, voir Limites). **Refondues en Phase 5**, voir section dédiée ci-dessous.

## Validé en navigateur réel (pas seulement `npm run build`)
L'intégralité des 5 parcours a été rejouée manuellement dans le navigateur (built-in browser tool), contre une instance réelle du backend (`uvicorn`) et la vraie base PostgreSQL, **sans mocks à aucun moment** : création de comptes (tuteur, enseignant, e-mails réels via Brevo), OTP, connexion, changement de mot de passe temporaire, inscription + validation, matricule généré et vérifié, candidature + notation IA réelle (échec de notation observé et corrigé manuellement, exactement le scénario que l'écran de révision manuelle est censé couvrir), création de contrat par un A+, **signature électronique par tracé au pointeur** (canvas → PNG → upload LuluFiles réel), publication de cours, génération réelle de quiz par FreeLLM (questions en français, pertinentes) et tentative notée, création de devoir et soumission avec **correction réelle par FreeLLM en arrière-plan** suivie via polling jusqu'au résultat, bulletin pondéré calculé correctement, réclamation de note soumise puis acceptée par l'A+, création d'établissement par l'A++ (e-mail temporaire réel envoyé à son A+), référentiel de coefficient créé.

**A révélé et corrigé 3 vrais bugs backend** (détail dans `backend/PROJECT_MAP.md`) :
1. `DocumentCandidatureOut` sans `id` — écran de révision manuelle inutilisable.
2. `ContratOut` sans `etablissement_id` — impossible pour l'enseignant de savoir où publier un cours à partir de ses contrats.
3. Aucune route pour lister les candidatures d'un poste — un A+ ne pouvait jamais créer de contrat sans déjà connaître l'id de la candidature.

**Et 1 vrai bug frontend, trouvé avant tout impact utilisateur** (pas encore exercé par un test manuel au moment de la découverte) : le type TS `PolitiqueDepassement` utilisait `"tirage_au_sort"` alors que la valeur JSON réelle exposée par le backend est `"tirage_sort"` (`.value` de l'enum Python, voir note dans `types/api.ts`) — aurait provoqué un mismatch silencieux (valeur non reconnue, filtrage tombant sur un cas par défaut) si un formulaire avait envoyé cette option sans jamais lever d'erreur explicite. Corrigé par relecture du modèle backend, pas par un crash observé.

## Parcours construits (étape 6) — Phase 2/3 (UC-11 à UC-19, sauf UC-19)
Frontend complet pour les 9 UC de la Phase 2/3, à l'exception explicite des visites virtuelles 3D/drone (UC-19), volontairement laissées à l'état de teaser « Bientôt disponible » sur `LandingPage.tsx` (décision utilisateur — ne pas construire tant que le choix technique de la visite 3D elle-même n'a pas été arbitré).
- **Messagerie (UC-13)** : `src/pages/messagerie/MessagerieListPage.tsx` (liste conversations) + `ConversationPage.tsx` (fil DM/groupe, signalement, masquage) pour tuteur/élève/enseignant ; `SignalementsPage.tsx` (modération) côté A+ ; entrée « Contacter [enfant] » sur `TuteurDashboard` (crée le DM via `eleve_utilisateur_id`, nouvellement exposé par le backend pour cet usage).
- **El Professor (UC-14, refondu le 2026-09-27)** : composant commun `src/components/el_professor/ElProfessorChat.tsx` (+ `.css`) — liste de conversations (recherche, tri par activité) et fil (un panneau à la fois sous 768 px, fil en plein écran), réponse en flux SSE (`api/el_professor.ts::poserQuestionEnFlux`, fetch + rafraîchissement du jeton via `client.ts::rafraichirUneFois`), arrêt/réessai, pièce jointe image/PDF (bouton, glisser-déposer, coller), dictée (Web Speech API du navigateur, FreeLLM ne transcrivant pas l'audio), copier, écouter (`/el-professor/synthese-vocale`), renommer/supprimer. Rendu `MarkdownIA.tsx` (react-markdown + remark-gfm/math + rehype-katex, chargé à la demande ; `\(…\)` et `\[…\]` convertis). Pages : `eleve/ElProfessorElevePage.tsx` (onglets « Mes conversations » / « Avec ma famille », `?cours=` ouvre la conversation d'un cours — lien depuis `CoursDetailPage`), `enseignant/ElProfessorPage.tsx`, `tuteur/ElProfessorTuteurPage.tsx` (onglets perso/famille + alertes). Entrée « El Professor » dans le menu des trois rôles (`AppLayout.tsx`, libellé court « El Prof » en barre mobile).
- **Cours en direct (UC-16)** : `enseignant/SessionsLivePage.tsx` (planifier/démarrer/terminer), `eleve/CoursDirectPage.tsx` (rejoindre), consentement caméra ajouté comme action sur `TuteurDashboard` (par enfant, état suivi uniquement côté client car aucun endpoint de lecture du consentement n'existe côté backend). Le `token_connexion` retourné par le backend est un placeholder (pas de SFU/WebRTC réel branché, voir docstring `_nouveau_token()` côté backend) — l'UI ne fait qu'afficher un état « en direct », aucun flux vidéo réel.
- **Transport & cantine (UC-11/12)** : `components/services_scolaires/ServicesScolairesPanel.tsx` (composant partagé achat+historique+remboursement, paramétré par `etablissementId`/`eleveUtilisateurId` pour servir aussi bien élève que tuteur sans dupliquer la logique), pages fines `eleve/ServicesScolairesPage.tsx` et `tuteur/ServicesScolairesPage.tsx` (le second résout l'établissement de l'enfant en croisant `classe_id` avec `listerClasses()` de chaque établissement, faute d'endpoint « classe par id »), gestion A+ dans `ServicesScolairesAdminPage.tsx`.
- **Billetterie (UC-17)** : `admin_etablissement/EvenementsAdminPage.tsx` (créer/annuler, désigner parrain et contrôleur), `billetterie/BilletteriePage.tsx` partagée (tuteur/élève/enseignant/A+, achat self-service uniquement — le backend n'autorise pas un tuteur à acheter un billet pour son enfant, contrairement au transport/cantine, cf. `acheter_billet` qui ne prend aucun `eleve_utilisateur_id`).
- **Micro-jobs (UC-18)** : `micro_jobs/MicroJobsPage.tsx` partagée enseignant/tuteur/A+/A++/**élève** (accessible côté route `/micro-jobs`, tous roles) — **correction (2026-09-26, Phase 5)** : l'élève n'est PAS exclu côté backend côté client (il peut publier une offre et payer, `_ROLES_CLIENT` l'inclut), seul le côté **prestataire** (accepter une mission rémunérée) l'exclut (`_ROLES_PRESTATAIRE`, âge légal de rémunération, ADR-008) — la mention précédente ("rôle élève explicitement exclu côté backend") était imprécise, corrigée ici. `admin_ministeriel/MicroJobsArbitragePage.tsx` (trancher une contestation, reverser un prestataire).
- **Contrôle d'accès partagé** : `controle_acces/ValiderAccesPage.tsx`, une seule page pour valider un ticket transport/cantine ou un billet d'événement (sélecteur de type + saisie manuelle de l'identifiant — voir Limites).
- Raccourcis ajoutés sur tous les tableaux de bord (`EleveDashboard`, `EnseignantDashboard`, `TuteurDashboard`, `AdminEtabDashboard`, `AdminMinisterielDashboard`) vers ces nouveaux écrans.

## Parcours construits (étape 6) — Phase 4 (UC-20/21/22, marketplace étudiante)
- `src/api/marketplace.ts` — un module par domaine, même convention que les autres (`micro_jobs.ts`, `billetterie.ts`).
- **Élève** : `src/pages/eleve/MarketplacePage.tsx`, page unique (même densité que `MicroJobsPage.tsx`) combinant catalogue filtrable (catégorie/état, `AnnonceMarketplaceOut` sans photos — résolues à la demande via `obtenirAnnonce()` par annonce, jamais en masse, même principe que les photos d'établissement ADR-009), publication (multipart, `<input type="file" multiple>`, au moins une photo obligatoire côté backend), réservation + paiement Kkiapay (même pattern « offre en attente de paiement » que `MicroJobsPage`), « Mes annonces » (retrait tant que `disponible`) et « Mes transactions » (déclarer la remise côté vendeur, confirmer/contester côté acheteur). Résolution de l'établissement de l'élève via `EleveMeOut.etablissement_id` (`EleveProfileContext`, déjà exposé, aucun nouvel endpoint nécessaire).
- **A+ (admin établissement)** : `src/pages/admin_etablissement/MarketplaceAdminPage.tsx` — signalements en attente (traiter), catalogue de l'établissement avec retrait direct (deux appels `disponible`+`reservee`, pas de filtre "tous statuts" côté backend), et un panneau « Litige et reversement » calqué sur `MicroJobsArbitragePage.tsx` (identifiants de contestation/transaction saisis manuellement — voir Limites).
- **Correction trouvée en construisant cette page (étape 6)** : le backend restreignait la lecture du catalogue (`GET .../marketplace/annonces` et `GET /marketplace/annonces/{id}`) aux seuls élèves — impossible pour l'A+ de consulter une annonce, alors qu'UC-20 prévoit explicitement qu'il puisse retirer une annonce "sans devoir attendre un signalement". RBAC élargi à l'A+ de l'établissement concerné côté backend (`backend/app/modules/marketplace/router.py`), avec un test dédié.
- Raccourcis ajoutés : entrée « Marketplace » sur la nav élève et A+ (`AppLayout.tsx`).

## Parcours construits (étape 6) — Phase 5 (UC-23 à UC-38, refonte admin ministériel)

Refonte complète du portail A++, jusqu'ici limité à 3 pages isolées — voir
`docs/cahier-des-charges-refonte-admin-ministeriel.md` et
`docs/diagrammes-uml-phase-5-admin-ministeriel.md`.

- `src/components/DataTable.tsx` — composant générique (tri via colonnes déjà triées côté
  appelant, pagination serveur ou statique, recherche dynamique, filtres custom, sélection
  multiple + barre d'actions groupées contextuelle), socle de tous les écrans de ce lot.
  Conçu pour être réutilisable par d'autres profils plus tard, mais seuls les écrans A++
  le consomment dans ce lot (pas de dérive de périmètre).
- `src/api/admin.ts` — nouveau module regroupant les appels de supervision transverse
  (utilisateurs, cours, devoirs, événements, journal d'audit) ; `etablissements.ts` et
  `evaluations_gouvernance.ts` et `micro_jobs.ts` étendus pour les capacités existantes.
- **`EtablissementsPage`** (refondue) : datatable avec recherche/filtre/sélection, actions
  groupées suspendre/réactiver (motif obligatoire), fiche détaillée par clic sur une ligne
  (description éditable + `PhotosEtablissementManager` déjà existant, réutilisé tel quel —
  l'A++ peut désormais gérer les photos/description de n'importe quel établissement, pas
  seulement l'A+ propriétaire, le backend l'autorisait déjà via `verifier_portee_etablissement`).
- **`ReferentielsPage`** (refondue) : datatable, édition directe du coefficient d'un
  référentiel en vigueur (icône crayon inline), validation groupée des propositions en
  attente, autocomplétion niveau/matière (`<datalist>`, dérivée des valeurs déjà chargées,
  aucun nouvel endpoint).
- **`MicroJobsArbitragePage`** (refondue) : deux files d'attente (`DataTable`) — contestations
  en attente et missions à reverser — avec tout le contexte (montant, parties, motif,
  contact mobile money du prestataire) chargé avant la décision. Remplace la saisie
  manuelle d'un identifiant technique (limite connue depuis la Phase 2/3, voir ci-dessous).
- **`UtilisateursPage`** (nouveau) : recherche nationale par nom/e-mail/matricule, filtre
  rôle/statut, suspension/réactivation de compte (motif obligatoire pour suspendre,
  auto-suspension bloquée côté backend).
- **`ContenusPage`** (nouveau) : supervision agrégée des cours et devoirs (deux datatables),
  masquage/démasquage non destructif (motif obligatoire, exclu de la vue élève).
- **`EvenementsSupervisionPage`** (nouveau) : supervision agrégée des événements, annulation
  d'urgence (le RBAC `annuler_evenement` autorisait déjà l'A++ via `_est_organisateur`,
  aucun changement backend nécessaire pour ce point précis).
- **`JournalAuditPage`** (nouveau) : lecture seule du nouveau journal d'audit ministériel,
  filtrable par type de cible.
- Nav (`AppLayout.tsx`) et tableau de bord (`AdminMinisterielDashboard.tsx`) étendus avec
  les 4 nouveaux modules.
- **Bug réel trouvé en écrivant `AdminUtilisateurOut`** : le champ `email` avait d'abord été
  typé `EmailStr` côté backend (même convention que `MeOut`) — mais cette liste agrège
  potentiellement des milliers de comptes, et une seule adresse mal formée dans un jeu de
  données ancien (seed généré avant que `84aef93` corrige le domaine `.test` → `.example`)
  faisait échouer (500) l'écran de supervision tout entier. Reproduit en se connectant en
  navigateur réel contre les données de `seed_mega.py` déjà présentes en local (6227
  utilisateurs) : `GET /me` puis `GET /admin/utilisateurs` renvoyaient 500 sur des comptes
  seedés avec un e-mail `.test`. Corrigé en repassant `AdminUtilisateurOut.email` en `str`
  simple (pas de perte : c'est un champ d'affichage, jamais réinjecté dans un formulaire).
- Validé par `tsc -b` + `vite build` (aucune erreur) et par des appels réels en navigateur/
  curl contre le backend réel et les données `seed_mega.py` (établissement suspendu/
  réactivé avec disparition/réapparition dans l'annuaire public, référentiel validé en lot
  puis modifié en ligne, compte enseignant suspendu puis bloqué sur un endpoint protégé
  puis réactivé, chaque action retrouvée dans `GET /admin/journal-audit`) — pas un parcours
  manuel exhaustif page par page comme la Phase 1, pour limiter le coût (voir demande
  explicite de l'utilisateur de vérifier le fonctionnement structurel plutôt que le rendu).

## Parcours construits (étape 6) — Phase 6 (UC-39 à UC-70, refonte admin établissement)

Refonte complète du portail A+ — voir `docs/cahier-des-charges-refonte-admin-etablissement.md`
et `docs/diagrammes-uml-phase-6-admin-etablissement.md`. Backend validé en amont endpoint par
endpoint (175/175 tests, détail dans `backend/PROJECT_MAP.md`) avant tout code frontend, comme
pour les phases précédentes.

- **`RentreePage`** (nouveau) : déclarer une rentrée (auto-clôture de la précédente côté
  backend), historique des rentrées avec statut, « Inviter les tuteurs » (notification e-mail
  de masse, résultat `nb_tuteurs_notifies` affiché).
- **`VieScolairePage`** (nouveau) : recherche par `eleve_utilisateur_id` (route ou champ
  manuel), accessible dès qu'une inscription (même en attente) a existé une fois pour cet
  établissement (RBAC backend, pas de logique dupliquée côté client) — photo affichée
  uniquement si `est_etudiant` (jamais pour un élève EP/ES, cf. UC-42), inscriptions et
  bulletins complets tous établissements/années confondus.
- **`ClassesPage`** (réécrite) : select niveau dépendant du type d'établissement
  (`NIVEAUX_PAR_TYPE`, reproduit depuis `scripts/seed_mega.py` — filière volontairement
  laissée en texte libre avec autocomplétion `<datalist>`, jamais un enum, cf. décision
  documentée dans le diagramme de classes Phase 6), année académique, reconduction en lot
  (sélection multiple + `DataTable`), lien « Console » par classe.
- **`ConsoleEtablissementPage`** (nouveau) : pivot lisant `classe_id` en query param, sélecteur
  d'objet (élèves/enseignants/tuteurs/matières/notes) × année académique, un `DataTable`
  paginé par objet — flexible par classe ou par établissement entier selon que `classe_id`
  est renseigné, conformément à la demande explicite de l'utilisateur.
- **`FormulaireBuilder`/`FormulaireDynamique`** (nouveaux composants partagés) : un seul
  moteur de formulaire dynamique (schéma JSON `ChampFormulaire[]`) réutilisé pour le
  recrutement (`RecrutementPage`/`PostulerPage`) et les actes académiques
  (`ActesAdminPage`/`ActesPage`) — jamais deux implémentations. Les champs de type `fichier`
  ne sont jamais rendus par `FormulaireDynamique` (uploadés séparément après création du
  parent, cf. `champsFichierDe()`).
- **Actes académiques** : document final téléchargeable via lien signé LuluFiles
  (`obtenirLienDocumentActe`) dès que l'A+ le livre (`ActesAdminPage`, section « Documents à
  livrer »).
- **Ticketerie QR (UC-54/68)** : bouton « PDF » (icône `Download`) sur chaque ticket payé
  (transport/cantine dans `ServicesScolairesPanel.tsx`, billet dans `BilletteriePage.tsx`),
  téléchargement en blob authentifié (`utils/telechargerBlob.ts::ouvrirBlobPdf` — un lien
  `<a href>` direct ne porterait pas le token Bearer). `ValiderAccesPage` gagne un mode
  « Scanner un QR code » (API navigateur native `BarcodeDetector`, pas de nouvelle dépendance
  npm ; message de repli explicite si le navigateur ne la supporte pas) en plus de la saisie
  manuelle déjà existante — le jeton scanné (`"{type}:{ticket_id}"`) pré-remplit le formulaire
  existant plutôt que de valider automatiquement, pour éviter une double validation accidentelle
  en cas de scan continu.
- **Restriction étudiants (UC-57/58)** : `GET /me` et `GET /eleves/me` exposent désormais
  `est_etudiant` (calculé une seule fois côté backend, `app.core.etudiant.est_etudiant`) —
  `MicroJobsPage` l'utilise pour n'afficher « Accepter » une offre qu'aux étudiants (adultes
  et élèves EP/ES voient un badge « Réservé aux étudiants » à la place, cohérent avec la
  règle : le rôle PRESTATAIRE est désormais étudiant-only, y compris pour les adultes qui y
  avaient accès avant cette phase), et `MarketplacePage` bloque entièrement l'accès aux
  élèves non-étudiants avec un écran dédié plutôt que de laisser échouer la publication au
  moment de la soumission.
- **Bug réel trouvé en écrivant cette section** : avant cette phase, `MicroJobsPage.tsx`
  gate `estEleve` bloquait tous les élèves (y compris les étudiants, désormais seuls
  éligibles) tout en laissant les adultes accepter des offres — l'exact inverse de la
  règle validée par l'utilisateur. `MarketplacePage.tsx` affichait encore un texte
  « réservé aux élèves de 16 ans ou plus » (ancienne règle d'âge, remplacée par la règle
  étudiant/non-étudiant). Corrigé en ajoutant `est_etudiant` à `MeOut`/`EleveMeOut` plutôt
  que de dupliquer un calcul d'âge ou de rôle côté frontend.
- Validé par `tsc -b` + `vite build` (aucune erreur) après chaque lot de pages ; pas de
  parcours manuel en navigateur pour cette phase (demande explicite de l'utilisateur de
  vérifier le fonctionnement structurel plutôt que le rendu visuel).

## Parcours construits (étape 6) — Phase 5 (volet Professeur, UC-23 à UC-28)

- **Mes salles (UC-24)** : `src/pages/enseignant/MesSallesPage.tsx` — remplace le sélecteur de classe brut par une vue par salle (établissement, effectif, année académique, badge « professeur principal »), avec la liste nominative des élèves dépliable (`GET /classes/{id}/eleves`).
- **Vie scolaire (UC-23)** : intégrée directement dans `MesSallesPage.tsx` (composant `VieScolaireEleve`, dépliable sous chaque élève) — formulaire d'ajout (nature, matière ou case « entrée générale » si professeur principal) + historique. Pas de page dédiée séparée : le contexte (classe + élève) est toujours nécessaire, même logique que le chat El Professor élève déjà en place côté cours.
- **Évaluations enrichies (UC-26)** : `MesDevoirsPage.tsx` — sélecteur nature formative/sommative à la création, boutons d'ajout de sujet/barème en document sur chaque devoir déjà créé, écran de correction manuelle étendu pour les soumissions par copie image (une note globale, pas de découpage par question). Côté élève, `DevoirDetailPage.tsx` : lien vers le sujet document s'il existe, et le placeholder « pièce jointe (bientôt disponible) » devient une vraie alternative fonctionnelle (« soumettre une photo de ta copie »).
- **El Professor enseignant (UC-27)** : `src/pages/enseignant/ElProfessorPage.tsx` — liste de conversations (par élève ou question générale) + chat, alerte visuelle (⚠️) sur tout message contenant une recommandation d'escalade. Côté administration, `src/pages/admin_etablissement/AlertesElProfessorPage.tsx` liste les alertes préparées par le garde-fou backend et permet de les marquer traitées.
- **Sessions live v2 (UC-25, le plus gros morceau)** : `src/pages/cours_direct/SalleLivePage.tsx` (route partagée `/salle-live/:sessionId`, enseignant et élève) — tableau collaboratif (`components/TableauCollaboratif.tsx`, `<canvas>` en coordonnées normalisées, outils craie/texte/chiffon, panneaux, file de demandes de craie côté professeur) + chat (`components/ChatSessionLive.tsx`), tous deux synchronisés en temps réel via un unique `WebSocket` ouvert par page (`ouvrirCanalTempsReelSessionLive`, voir `api/cours_direct.ts`). `SessionsLivePage.tsx` et `eleve/CoursDirectPage.tsx` gagnent un bouton « Ouvrir la salle », disponible dès `planifiee` (salle sociale pré-cours) pas seulement `en_cours`. La session (métadonnées) est transmise par `navigate(..., { state: { session } })` plutôt qu'un nouvel appel réseau — accès direct par URL sans état de navigation affiche un message de repli plutôt qu'un plantage.
- **Quick win contrôleur (UC-28)** : nouveau composant réutilisable `src/components/RechercheUtilisateurDesignable.tsx` (même pattern debounce/suggestions que `AffectationsClasseManager.tsx`), intégré dans `ServicesScolairesAdminPage.tsx` (désignation transport/cantine). **Non fait dans ce lot** : le champ de désignation contrôleur *par événement* dans `EvenementsAdminPage.tsx` et le champ « parrain » restent en saisie d'ID brut — même composant à réutiliser, laissé de côté pour rester dans le temps imparti.

**Validé par `tsc -b` (aucune erreur) et `vite build` (bundle généré sans nouvelle erreur), pas par un parcours manuel en navigateur** — même limite que les Phases 2/3/4 initialement (aucune instance Postgres locale disponible au moment de l'écriture ; le backend a depuis été vérifié contre un Postgres réel pour les migrations, voir `backend/PROJECT_MAP.md`, mais pas rejoué manuellement bout en bout côté UI). Le canal WebSocket lui-même n'a été vérifié qu'via les tests backend (`tests/test_cours_direct.py`, `websocket_connect` du TestClient) — jamais depuis un vrai navigateur dans cette passe. À rejouer avant mise en production : ouvrir une session live à deux comptes réels (professeur + élève) dans deux navigateurs, vérifier que les traits/permissions/messages se propagent bien en direct.

## Parcours construits (étape 6) — Phase 6 (volet Élève/Tuteur, UC-29 à UC-38)

- **Mutualisation** : `src/tuteur/useMesEnfants.ts` (hook) centralise le chargement des inscriptions validées avec enfant — utilisé par les 9 nouvelles pages tuteur ci-dessous plutôt que dupliqué page par page (contrairement au reste du frontend, qui duplique plutôt ce genre de logique ; ici le nombre de pages concernées justifiait l'exception).
- **Vie scolaire (UC-30.1)** : `src/pages/tuteur/VieScolaireEnfantPage.tsx` — réutilise `listerVieScolaireEleve()` déjà existant (créé côté enseignant en Phase 5), le backend l'autorisait déjà pour TUTEUR.
- **Suivi devoirs (UC-31)** : `src/pages/tuteur/DevoirsEnfantPage.tsx` — nouvelle fonction `obtenirSoumissionDeMonEnfant()` dans `api/evaluations.ts`.
- **Marketplace, lecture seule (UC-34)** : `src/pages/tuteur/MarketplaceEnfantPage.tsx` — `annoncesDeMonEnfant()`/`transactionsDeMonEnfant()` (`api/marketplace.ts`), aucune action d'achat/publication exposée (cohérent avec le backend, strictement lecture).
- **Résumé de session live (UC-33)** : `src/pages/tuteur/SessionsLiveEnfantPage.tsx` — liste les sessions (`listerSessionsLive()`, déjà autorisé pour TUTEUR côté backend), bouton « Voir le résumé » à la demande pour les sessions `terminee` (`obtenirResumeSessionLive()`), jamais de tentative de rejoindre une session en direct.
- **El Professor Tuteur (UC-32)** : `src/pages/tuteur/ElProfessorTuteurPage.tsx` — même structure que `enseignant/ElProfessorPage.tsx` (liste de conversations + chat), sélecteur d'enfant au lieu d'un sélecteur d'élève de classe, section alertes de sécurité concernant l'enfant sélectionné.
- **El Professor Famille (UC-37, innovation)** — onglet « famille » des pages El Professor tuteur et élève (anciennes pages dédiées supprimées ; les routes `/…/el-professor-famille` ouvrent cet onglet) : le tuteur invite, l'enfant voit une pastille et un bandeau « Rejoindre », seul le tuteur peut renommer/supprimer le fil. Les messages affichent explicitement l'auteur (« Vous » / « Votre enfant » / « Votre tuteur ») pour lever toute ambiguïté dans un fil à trois participants (élève, tuteur, IA).
- **Coffre-fort familial (UC-35, innovation)** : `src/pages/tuteur/CoffreFortPage.tsx` — formulaire plafond/seuil (opt-in, champs vides = aucune limite), section « dépenses en attente de validation » (approuver/refuser), relevé financier, historique des dépassements. Côté élève, `src/components/coffre_fort/ValidationsEnAttenteBanner.tsx` (intégré à `EleveDashboard.tsx`) rend visible qu'une dépense est bloquée en attente du tuteur — jamais un blocage silencieux, même si l'élève ne peut rien y faire lui-même.
- **Radar familial (UC-36, innovation)** : `src/pages/tuteur/RadarFamilialPage.tsx` — affiche le résumé narratif et la liste brute des sources citées (transparence : le texte généré n'est jamais la seule preuve présentée).
- **Passeport de compétences (UC-38, innovation)** : composant partagé `src/components/passeport/PasseportPanel.tsx` (badges, moyennes, quiz réussis, cours suivis, export PDF ouvert dans un nouvel onglet) réutilisé par `eleve/PasseportPage.tsx` et `tuteur/PasseportEnfantPage.tsx` — même pattern de composant-panneau partagé que `ServicesScolairesPanel.tsx` (Phase 2/3).
- Raccourcis ajoutés : grille de navigation `TuteurDashboard.tsx` (9 nouvelles entrées) et `EleveDashboard.tsx` (El Professor Famille, Passeport).

**Validé par `tsc -b` (aucune erreur), `vite build` (bundle généré) et `oxlint` (0 erreur, uniquement des warnings déjà présents partout ailleurs dans le projet) — ET, contrairement aux Phases 2 à 5, par un parcours manuel complet en navigateur réel** : serveur backend lancé avec base SQLite jetable et `get_email_client`/`get_llm_client`/`get_files_client`/`get_session_factory` substitués par des doublures de test (même principe que `tests/conftest.py`), un établissement/classe/enseignant (professeur principal)/tuteur/élève créés via de vrais appels HTTP (pas d'insertion directe en base), puis Playwright (Chromium headless déjà présent dans l'environnement) piloté avec de vrais jetons JWT pour visiter les 10 nouvelles routes tuteur et les 2 nouvelles routes élève. Parcours vérifiés bout en bout avec de vraies données : résumé de session live généré à la demande, invitation El Professor Famille → l'élève rejoint → échange de messages avec attribution de rôle correcte, formulaire Coffre-fort enregistré et persistant après rechargement. Zéro erreur console (une seule ligne `ERR_CERT_AUTHORITY_INVALID` sans rapport, liée à l'interception TLS du bac à sable, pas à l'application).

## Bulletin détaillé (2026-09-28)
`components/bulletin/BulletinDetail.tsx` (périodes, moyenne, décision, PDF, notes par matière) partagé
par `eleve/BulletinPage` et `tuteur/BulletinsEnfantPage` (route `/tuteur/bulletins?enfant=`, menu parent
« Bulletins », lien depuis `TuteurDashboard`).

## Saisie papier (2026-09-28)
Détail : `docs/saisie-papier.md`. `pages/admin_etablissement/SaisiePapierPage.tsx` (route
`/admin-etablissement/saisie-papier`, menu A+ en 3e position) ; `components/saisie_papier/PrisePhotos.tsx`
(capture appareil photo / fichiers) et `CopiesPapier.tsx` (aussi dans `enseignant/MesDevoirsPage`) ;
« Signé sur papier » dans `RecrutementPage` ; `api/saisie_papier.ts`.

## Documents officiels (2026-09-28)
Détail : `docs/documents-officiels.md`. `components/ConseilDeClasse.tsx` (professeur principal,
dans `enseignant/MesSallesPage`) ; `components/BoutonBulletinPdf.tsx` (parent, `TuteurDashboard`) ;
bouton PDF dans `eleve/BulletinPage`, `enseignant/MesContratsPage`, `admin_etablissement/RecrutementPage` ;
`api/client.ts` relit les erreurs JSON reçues en Blob (téléchargements).

## Audit d'ergonomie du 2026-09-28
Détail : `docs/audit-ergonomie-2026-09-28.md`. Points de repère :
- `components/Modale.tsx` : `Modale` (dialogue accessible, panneau bas sur téléphone) et
  `ConfirmationProvider` / `useConfirmation()` (monté dans `App.tsx`) — obligatoire avant toute
  action irréversible ou groupée.
- `components/ui.tsx` : `SuccessBanner` = notification flottante auto-masquée ; `ErrorBanner`
  défile jusqu'à être visible ; `Field` relie étiquette et champ ; `TextInput`/`Select` ont un
  nom accessible par défaut hors `Field`.
- `utils/libelles.ts` : `libelle(valeur)` pour tout statut/rôle/type/période affiché.
- `layout/AppLayout.tsx` : barre du bas = 4 entrées + « Plus » (menu complet, déconnexion) ;
  pastilles `useCompteurs()` (`GET /me/compteurs`).
- `components/GuideDemarrage.tsx` : guide de première connexion par rôle (5 tableaux de bord).
- `pages/eleve/EleveDashboard.tsx` réécrit sur données réelles ; `BulletinPage` par période
  (`periodesDeLaClasse`) ; `ReferentielsEtabPage` filtrée sur les niveaux de l'établissement.
- `scripts/audit_ergonomie.js` : audit automatisé dans le navigateur (débordements, valeurs
  brutes, accents, champs sans étiquette, cibles tactiles…) ; `scripts/textes_affiches.cjs` :
  extraction des textes affichés via le compilateur TypeScript.

## Audit de sécurité du 2026-09-27
Détail : `docs/audit-securite-2026-09-27.md`. Côté frontend :
- `api/client.ts` : l'intercepteur 401 ignore les appels `/auth/*` (un mauvais mot de passe ou un code OTP erroné redirigeait vers `/connexion` et effaçait l'erreur).
- `api/auth.ts::changerMotDePasse` stocke la paire de tokens renvoyée (les autres sessions sont révoquées côté serveur) ; `renvoyerCodeOtp`, `demanderReinitialisation`, `reinitialiserMotDePasse`.
- `pages/MotDePasseOubliePage.tsx` (route `/mot-de-passe-oublie`, lien depuis `LoginPage`) ; bouton de renvoi du code dans `SignupPage`.
- `RecrutementPage` : panneau casier judiciaire (statut, consultation confidentielle en blob, verdict) ; le formulaire de contrat n'apparaît qu'après un verdict « conforme ».
- `MarketplaceAdminPage` : liste « vendeurs à payer » (fin de la saisie manuelle d'ID pour le reversement).
- `vercel.json` / `netlify.toml` : en-têtes de sécurité dont une **Content-Security-Policy** (même valeur dans `vite.config.ts`, appliquée par `vite preview`) — toute nouvelle ressource externe (script, image, iframe) doit y être ajoutée dans les trois fichiers ; `vite.config.ts` : cible du proxy surchargeable par `LULU_API_PROXY`.
- `KkiapayButton` : prop obligatoire `typeRessource` (forme le `partnerId` que le webhook utilise pour identifier la ressource payée) ; un seul écouteur Kkiapay global.
- `ConversationPage` : messages chargés par pages de 100, bouton « Charger les messages précédents ».
- Vérifié en navigateur contre un backend réel (PostgreSQL, services externes simulés) : erreur de connexion, mot de passe oublié, OTP erroné + renvoi, verdict casier, reversement vendeur.

## Limites connues (non bloquantes pour un MVP, à traiter avant une mise en production plus large)
- Pas de vue A+ pour proposer une révision de référentiel de coefficient (`POST /referentiels-coefficients/{id}/proposition`) — seule la création/validation côté A++ a une UI.
- La correction manuelle d'une soumission en échec IA (`MesDevoirsPage`) affiche le texte de la réponse et un champ de points par question, mais pas le corrigé/barème attendu côté enseignant au même endroit (il doit s'en souvenir ou rouvrir le devoir).
- `MesCoursPage`/`MesDevoirsPage` affichent l'établissement par son id si `listerEtablissements()` n'a pas encore résolu au moment du rendu (le nom apparaît dès que la requête aboutit) — cosmétique, pas fonctionnel.
- Pas de tests automatisés frontend (ni unitaires ni end-to-end) — seule la validation manuelle en navigateur ci-dessus existe. À évaluer avant la mise en production (Playwright ou équivalent).
- **Désignation de contrôleur/parrain (UC-11/12/17)** : **partiellement résolu en Phase 5 (UC-28)** — `ServicesScolairesAdminPage.tsx` (transport/cantine) utilise désormais une recherche par nom (`RechercheUtilisateurDesignable`, endpoint `GET /etablissements/{id}/utilisateurs-designables`). Le contrôleur *par événement* dans `EvenementsAdminPage.tsx` et le champ « parrain » d'un événement restent en saisie d'ID brut — même composant réutilisable, pas encore branché là.
- **Validation d'un ticket/billet (`ValiderAccesPage`)** (le reversement marketplace a désormais sa file, audit 2026-09-27) : même limite — aucun endpoint ne liste les tickets/transactions en attente pour un contrôleur/arbitre donné, la saisie de l'identifiant est manuelle. Fonctionnel (le backend valide bien les droits), mais suppose une communication de l'identifiant hors plateforme (guichet physique avec justificatif, ticket de support, etc.). **L'arbitrage micro-job n'a plus cette limite depuis la Phase 5** (`MicroJobsArbitragePage` a désormais une vraie file d'attente avec tout le contexte) — le même pattern (`GET /marketplace/contestations` avec contexte enrichi) pourrait être repris pour la marketplace dans un lot futur, hors périmètre de ce lot ministériel.
- **Frontend Phase 2/3 validé par `tsc -b` + `vite build` + suite pytest backend (124/124), pas par un parcours manuel complet en navigateur rôle par rôle** comme la Phase 1 (§ ci-dessus) — la création de comptes de test pour les 9 UC (tuteur/élève/enseignant/A+/A++, inscriptions validées, contrats signés, etc.) n'a pas été rejouée dans cette passe pour limiter le coût. Seule la landing page (page publique, sans authentification) a été vérifiée en navigateur réel (rendu de la nouvelle section « Au-delà de la classe » et du badge « Bientôt disponible », zéro erreur console). À faire avant mise en production.
- **Frontend Phase 4 (marketplace) même limite que ci-dessus** : validé par `tsc -b` (aucune erreur) + `vite build` (bundle généré sans nouvelle erreur) + suite pytest backend (144/144, RBAC élargi inclus), pas par un parcours manuel en navigateur — aucune instance Postgres locale disponible dans cet environnement de développement pour peupler des comptes de test réels (`seed_mega.py` exige une vraie base). À rejouer manuellement (élève : publier/réserver/payer/confirmer, A+ : signaler/retirer/trancher/reverser) dès qu'un Postgres local ou de staging est accessible, avant mise en production.

## Notes
- `.env.example` documente `VITE_KKIAPAY_PUBLIC_KEY`/`VITE_KKIAPAY_SANDBOX` — `.env` local non commité (gitignore racine).
- `.claude/launch.json` (racine du dépôt) définit le serveur de dev `frontend` pour `preview_start`, sur le port 5173.
- **Piège Vite/HMR rencontré (2 fois)** : supprimer une constante/un export encore référencé par une closure déjà montée (ex. retirer `TYPE_ICON` d'un fichier pendant qu'un composant l'utilisant est déjà rendu) peut laisser le module graph de Vite dans un état incohérent — `ReferenceError` en plein render, alors que `tsc --noEmit` est propre (la source ne référence plus rien d'indéfini, c'est un état HMR fantôme, pas un vrai bug). Un simple rechargement de page ne suffit pas toujours : `rm -rf node_modules/.vite` puis relancer complètement le serveur de dev (pas juste un `--reload`) résout le problème.

## Lot 7 — Conformité PAG et inclusion (2026-09-28)
Cahier des charges : `docs/cahier-des-charges-conformite-pag.md`.
- **Accessibilité (7.1/7.2)** : `src/accessibilite/` — `AccessibiliteContext.tsx` (préférences posées en
  attributs sur `<html>` : `data-taille`, `data-contraste`, `data-espacement`, `data-animations-reduites`,
  `data-donnees-reduites` ; traduites en styles dans la section « ACCESSIBILITÉ » de `index.css` ;
  `localStorage` `ls-accessibilite` + synchronisation `PUT /me/preferences-accessibilite`),
  `lecteurVocal.ts` (lecture à voix haute unique pour toute l'app : `speechSynthesis`, repli serveur,
  `useEtatLecture`), `BarreAccessibilite.tsx` (`AccessibiliteHote` monté une fois dans `AppLayout`,
  `BoutonAccessibilite` : flottant sur les pages publiques, dans la barre latérale, entrée
  « Accessibilité » du menu « Plus » sur téléphone ; raccourcis Alt+A / Alt+L). `public/preferences-initiales.js`
  applique thème et réglages avant le premier rendu (pas de flash). Lien « Aller au contenu » et `<main>`
  sur toutes les mises en page, `lang="fr"`.
- **Contrastes** : `.btn-primary` sur `--primary-deep` et texte vert en `--primary-deep` (le vert de marque
  n'atteignait que 3,3:1) ; en thème sombre, texte foncé sur les boutons colorés (`--on-*`).
- **Audit** : `scripts/audit_accessibilite.js` (axe-core, WCAG 2.1 AA, dans une iframe, même principe
  que `audit_ergonomie.js`). Critère : 0 violation critique/sérieuse — atteint sur 22 pages (5 rôles,
  clair/sombre, 375 px et 1280 px).
- **Connectivité limitée (7.5)** : toutes les routes en `lazy()` dans `App.tsx` (bundle initial
  945 Ko → 368 Ko, 111 Ko compressés) ; `useDonneesReduites()` coupe la scène Three.js, la photo de fond
  de la landing et le chargement automatique des photos (`Carousel`) ; PWA : `public/manifest.webmanifest`,
  `public/sw.js` (coquille en cache, contenus pédagogiques « réseau d'abord, copie sinon », vidés à la
  déconnexion, enregistré en production seulement dans `main.tsx`) ; `BandeauHorsLigne.tsx` ;
  `AuthContext` ne déconnecte plus sur une simple absence de réseau.
- **Handicap auditif (7.3)** : `src/components/transcription/` — `ChampTranscription`/`ChampSousTitres`
  (saisie ou dictée via `accessibilite/dictee.ts::useDictee`), `ModaleTranscription` (compléter un cours
  existant, proposition de mise en forme par l'IA à accepter explicitement), `LecteurCours` (lecteur
  audio/vidéo dans la page, `preload="none"`, sous-titres chargés en blob car `<track>` ne transmet pas
  le jeton) et `TranscriptionCours` (Markdown + « Écouter »). Badge « Transcription manquante » dans
  `MesCoursPage` ; « Écouter ce cours » sur les cours texte (`CoursDetailPage`).
- **Mode Écoute (7.4)** : `pages/tuteur/ModeEcoute.tsx` remplace `TuteurDashboard` quand
  `preferences.mode_ecoute` (activé par le bandeau « Mode Écoute » du tableau de bord ou le panneau
  d'accessibilité) : grandes tuiles pictogrammes qui parlent (`lecteurVocal`), flèche vers l'écran
  détaillé, consentement donné en un geste. Libellés enregistrés en langues nationales :
  `public/audio/ecoute/index.json` + `<langue>/<clé>.mp3` (aucun enregistrement livré pour l'instant ;
  repli sur la voix française). Messages vocaux : `components/messagerie/MessageVocal.tsx`
  (MediaRecorder Opus 24 kbit/s, 2 min max ; lecture à la demande), branchés dans `ConversationPage`.
- **Pilotage (7.6)** : `pages/admin_ministeriel/IndicateursPage.tsx` (routes `/admin-ministeriel/indicateurs`
  et `/admin-etablissement/indicateurs`, menu « Indicateurs ») : filtres année/département, tuiles, tableau
  par département avec barre d'effectifs, encart « Alignement PAG », export tableur ; `api/indicateurs.ts`.
  `components/ChoixTerritoire.tsx` (création d'établissement A++, `LocalisationEtablissementManager` A+).
  Sexe facultatif dans `NouvelleInscriptionPage` et l'inscription au guichet. La tuile « Couverture
  académique » codée en dur du tableau A++ est remplacée par les élèves inscrits réels.
- **Alphabétisation (7.7)** : `pages/tuteur/AlphabetisationPage.tsx` (`/tuteur/alphabetisation`, menu
  « Apprendre à lire », tuile « Apprendre à lire » du mode Écoute) : choix du centre, leçons à écouter,
  `components/alphabetisation/QuizOral.tsx` (question et réponses lues, grands boutons numérotés, essai non
  enregistré) ; `ApprenantsAdultesPanel` sur le tableau de bord A+ d'un centre `CA` ; type `CA` ajouté aux
  libellés, filtres de l'annuaire et des cartes, niveaux de `ClassesPage`, photos par défaut.
- **EFTP, stages, bourses (7.8)** : `pages/eleve/StagesPage.tsx` (`/eleve/stages`) et
  `pages/admin_etablissement/StagesAdminPage.tsx` (`/admin-etablissement/stages`) ; `components/insertion/
  ValiderCompetence.tsx` (dans `MesSallesPage`, sous la vie scolaire d'un élève) ; compétences dans
  `PasseportPanel` ; case « Bourse pour les filières scientifiques » dans `ActesAdminPage` et bandeau
  d'éligibilité dans `ActesPage` ; « Type d'enseignement » dans `ClassesPage` (ES/UP) ; tuiles EFTP et
  alphabétisation dans `IndicateursPage` ; `api/insertion.ts`.
- **File d'attente hors ligne (UC-80)** : `hors_ligne/fileAttente.ts` — `envoyerOuMettreEnAttente(url, corps, libellé)`
  envoie avec une clé `X-Cle-Idempotence` ; sans réponse réseau, garde l'envoi (`localStorage` `lulu-file-attente`)
  et le rejoue à l'événement `online`, à la reconnexion (`AuthContext`) ou via « Réessayer » du `BandeauHorsLigne` ;
  vidée à la déconnexion. Branchée sur les réponses de devoir (`DevoirDetailPage`), les messages texte
  (`ConversationPage`) et la vie scolaire saisie par l'enseignant (`MesSallesPage`). Jamais de paiement ni de fichier.
  Vérifié en réel : message envoyé site coupé, livré une seule fois au retour.
