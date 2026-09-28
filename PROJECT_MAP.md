# LuluSchools — Project Map

## Identité
Plateforme éducative nationale sous mandat ministériel (Bénin). Backend FastAPI/PostgreSQL — **toutes les phases connues à ce jour (UC-01 à UC-19) ont un backend complet, testé unitairement ET validé de bout en bout (124 tests)**. Frontend React (Vite/TS/Tailwind) — **les 5 rôles sont fonctionnels pour l'intégralité des 18 UC implémentés (Phase 1 + Phase 2/3)**, seules les visites virtuelles 3D/drone (UC-19) restent un teaser « Bientôt disponible » sur la landing page. Développé avec la méthode spec-first `lucio-dev`. Cahier des charges Phase 1 : `docs/cas-utilisation-phase-1.md` ; Phases 2/3 (cas d'utilisation, UML, contrat d'API, backend et validation de bout en bout validés — étape 6 frontend restante) : `docs/cas-utilisation-phase-2-3.md`, `docs/diagrammes-uml-phase2-3.md`, `docs/contrat-api-phase2-3.md`. Phase 4 (marketplace étudiante, nouveau lot) : cas d'utilisation, UML, contrat d'API, backend, validation de bout en bout et frontend faits (étapes 1-6, choix technique non repris sur demande explicite — aucune nouvelle intégration), étape 7 (intégration) pas encore démarrée : `docs/cas-utilisation-phase-4-marketplace.md`, `docs/diagrammes-uml-phase-4-marketplace.md`, `docs/contrat-api-phase-4-marketplace.md`. Décisions d'architecture : `docs/adr/`, avancement du pipeline : `SUIVI-PROJET.md`.

## Arborescence
- `backend/` — API FastAPI (monolithe modulaire) — voir `backend/PROJECT_MAP.md`
- `docs/` — spec, UML, ADR, contrat d'API
- `frontend/` — application React (Vite/TS/Tailwind) — voir `frontend/PROJECT_MAP.md`. Les 5 rôles (Tuteur, Élève, Enseignant, A+, A++) sont construits pour la Phase 1 (testés en navigateur contre le backend réel, sans mocks) et pour la Phase 2/3 (validé par `tsc -b`/`vite build`/suite pytest, pas encore par un parcours manuel complet en navigateur — voir Limites dans `frontend/PROJECT_MAP.md`).
- `render.yaml` — Blueprint de déploiement du backend sur Render, plan **gratuit** (Web Service + PostgreSQL, `databases:` géré par le Blueprint via `fromDatabase`, pas de disque persistant) — voir ADR-006 et `docs/deploiement-render-vercel.md`.
- `frontend/vercel.json`, `frontend/netlify.toml` — config de déploiement du frontend, deux plateformes équivalentes possibles (proxy `/api/*` vers le backend Render + repli SPA pour React Router, pas de CORS côté navigateur) — Netlify en solution de secours (limite de crédits sur son plan gratuit, voir `docs/deploiement-render-vercel.md`), voir ADR-006.
- `.github/workflows/backend-ci.yml`, `.github/workflows/frontend-ci.yml` — CI (tests pytest + migrations Alembic sur Postgres jetable ; lint + build frontend) sur chaque push/PR ; ne déploient rien, Render et Vercel déploient nativement via leurs propres intégrations Git — voir `docs/deploiement-render-vercel.md` § CI/CD.

## Points d'entrée
API backend sous préfixe `/api/v1` — contrat complet et à jour dans `docs/contrat-api-phase1.md`, ne pas le dupliquer ici.

## Conventions
- Pas de Docker (ADR-001) : venv Python natif, PostgreSQL natif. Déploiement : Render (backend) + Vercel/Netlify (frontend), pas de VPS — voir ADR-006 (révise le plan VPS initial de `docs/choix-technique-phase1.md`).
- Toute décision d'architecture structurante devient un ADR dans `docs/adr/`, jamais seulement actée en conversation.
- Un commit par artefact/endpoint livré (voir historique git) — pas de gros commits fourre-tout.

## Décisions d'architecture notables
- Monolithe modulaire, pas de microservices (ADR-001).
- Accès LLM (notation de documents, etc.) exclusivement via FreeLLM (service personnel, API compatible OpenAI), jamais l'API Anthropic en direct (ADR-002).
- Stockage de fichiers via LuluFiles, sauf le casier judiciaire qui reste local pour raisons légales — Art. 395 de la loi béninoise n° 2017-20 (ADR-003).
- Signature du contrat enseignant : tracé dessiné sur canvas (doigt/stylet), signature électronique simple, pas qualifiée — décision définitive de l'utilisateur (ADR-004).
- Notation/correction IA multi-appels (candidatures, devoirs) exécutée en arrière-plan (`BackgroundTasks`) pour ne jamais bloquer la requête sur la latence de FreeLLM ; génération de quiz (un seul appel) reste synchrone (ADR-005).
- Déploiement sur Render (backend, plan gratuit) + Vercel (frontend), pas de VPS ; casier judiciaire chiffré (Fernet) et stocké en base plutôt que sur disque (pas de disque persistant sur le plan gratuit) ; CORS évité côté navigateur via un rewrite Vercel plutôt qu'ouvert ; base PostgreSQL gratuite expire 30 jours après création, à surveiller (ADR-006, addendum 2026-09-25).
- Design system frontend recentré sur une identité institutionnelle (État béninois) : palette fonctionnelle sobre, ombres diffuses, typographie Rubik/JetBrains Mono/Itim (wordmark uniquement), zéro emoji sur la plateforme (icônes `lucide-react` exclusivement), gamification cantonnée aux écrans élève (ADR-007).
- Séquestre micro-jobs (UC-18) : Kkiapay n'offre pas de transfert ponctuel fiable vers un tiers (`setup_payout` existe mais configure une règle récurrente pour tout le compte, pas un virement par mission) — reversement au prestataire fait manuellement par un opérateur en V1, LuluSchools suit le séquestre comme un simple statut (ADR-008).
- Landing page : fond d'étoiles Three.js chargé à la demande + objets 3D flottants en CSS (jamais l'inverse — cf. raisonnement LuluFiles cité dans l'ADR) ; vitrine établissements réduite à un teaser sur la landing page, liste complète déportée sur un annuaire public dédié et paginé (`/etablissements`) ; photos d'établissement via LuluFiles, liens signés résolus à la demande par établissement, jamais en masse (ADR-009).

## État d'avancement

**Phase 1** — étapes 1-6 validées. Étape 4 (backend) : tous les modules (UC-01 à UC-10) faits et testés (75 tests), 12 migrations appliquées en réel, mot de passe temporaire réellement appliqué côté serveur, notation/correction IA en arrière-plan (ADR-005). Étape 5 (validation de bout en bout) : scénario automatisé rejouant tout le parcours réel dans l'ordre — a révélé et corrigé un vrai bug (chemin du casier judiciaire mal interprété sous Windows). Étape 6 (frontend) : **les 5 rôles de la Phase 1 sont construits et testés en navigateur reel contre le backend reel**, sans mocks — Tuteur (inscription, consentement), Élève (cours, quiz IA, devoir corrigé par IA en arrière-plan, bulletin, réclamation), Enseignant (candidature, contrat signé par tracé canvas, cours/quiz/devoirs), A+ (validation d'inscriptions, classes, recrutement complet jusqu'au contrat, contestations, actes), A++ (création d'établissement, référentiels de coefficients). Ce test manuel a révélé et corrigé 3 vrais bugs backend et 1 bug frontend (détail dans `backend/PROJECT_MAP.md` et `frontend/PROJECT_MAP.md`).

**Phase 2/3** — étapes 1 à 6 validées (voir `SUIVI-PROJET.md`) : cas d'utilisation, diagrammes UML, contrat d'API, **backend complet** pour les 9 UC (UC-11 à UC-19) — tickets transport/cantine, contrôle d'accès, billetterie, messagerie, assistant El Professor, cours vidéo, cours en direct, visites 3D/drone, micro-jobs+séquestre — et **validation de bout en bout** (`backend/tests/test_e2e_parcours_phase2_3.py`, même principe que `test_e2e_parcours_complet.py` : un seul établissement/classe/enseignant/élève/tuteur réutilisés à travers les 9 UC dans l'ordre réel, paiement Kkiapay réellement bouclé à chaque étape payante). 8 nouveaux modules, 8 migrations (0013-0020) appliquées en réel, 124 tests au total (aucune régression). Étape 6 (frontend) : **8 des 9 UC ont une interface complète** — messagerie, El Professor, cours en direct, transport/cantine, billetterie, micro-jobs — pour les 5 rôles concernés, réutilisant le design system institutionnel (ADR-007/009) ; seul UC-19 (visites 3D/drone) reste un teaser « Bientôt disponible », par décision explicite de l'utilisateur (le choix technique de la visite 3D elle-même n'a pas encore été arbitré). Détail par module dans `backend/PROJECT_MAP.md` et `frontend/PROJECT_MAP.md`. Prochaine étape : 7 (intégration/correction des écarts) puis 8 (déploiement) pour ce lot Phase 2/3.

## Dernière synchronisation
2026-09-27 (audit de sécurité, branche `audit/securite-approfondie`) — Audit profond du
backend (243 endpoints), du frontend et de l'historique git : 31 constats corrigés, dont un
bug bloquant en production invisible sous SQLite (`DISTINCT` sur colonne `json` : écran
Recrutement de l'A+ inutilisable sur PostgreSQL), des IDOR (cours/fichiers, bulletins
enregistrés pour n'importe quel élève), un contournement des frais d'actes, une
réinscription qui recréait compte et matricule, un consentement parental auto-déclarable
par un mineur, un casier judiciaire jamais vérifiable ni purgé (Art. 395), des vendeurs et
prestataires jamais payés en cas de validation tacite, et une API qui gelait pendant chaque
téléversement. Nouveaux parcours : renvoi d'OTP, mot de passe oublié, verdict casier, file de
reversement marketplace. Migration `0016`. Suite de tests rejouable sur PostgreSQL
(`LULU_TEST_DATABASE_URL`). Seconde passe le même jour (12 constats de plus) : paiements
rattachés par `partnerId`, limitation de débit en base, CSP, migration `0017` (aucune dérive
de schéma), tests PostgreSQL en CI, arbitrages messagerie/contrôleurs, parcours navigateur de tous les rôles (PATCH /me pour le numéro Mobile Money), puis **refonte d'El Professor en interface de chat complète**
(flux SSE, pièces jointes image/PDF, aide générale de l'élève, synthèse vocale, migration `0018`,
vérifiée contre le vrai FreeLLM), plafonds de tokens retirés (1000 messages/jour), et
**seed réécrit** (`backend/scripts/seed_donnees/`, UAC toujours présente, auto-vérifié sur
39 règles métier, `seed_render.bat` pour la base en ligne), migration 0017 rendue idempotente
(échec du déploiement Render), puis **simplification de l'administration** (boîte « À traiter »,
automatisations, actions groupées, IA qui prépare, remboursements Kkiapay automatiques, migration
`0019`, voir `docs/simplification-administration.md`), puis **audit d'ergonomie** des 79 pages
(menu mobile complet, confirmations, notifications, libellés, pastilles `GET /me/compteurs`,
guide de première connexion, bulletins par trimestre/semestre, messages accentués ; voir
`docs/audit-ergonomie-2026-09-28.md`), puis **documents officiels** (bulletin PDF par période,
contrat signé en PDF, certificat de réussite automatique, conseil de classe ; voir
`docs/documents-officiels.md`), puis **saisie papier** pour les personnes sans smartphone
(feuille de notes, appel, cours, copies, inscription au guichet, consentement et contrat signés
sur papier ; migration `0020` ; voir `docs/saisie-papier.md`). 341 tests au vert
sous SQLite et PostgreSQL. Rapport, actions hors code (rotation du mot de passe DB exposé
dans l'historique git, secrets Render) et risques résiduels :
`docs/audit-securite-2026-09-27.md`.

2026-09-26 (Phase 6, frontend) — Étape 6 du lot Phase 6 (UC-39 à UC-70, refonte admin
établissement) : 4 nouvelles pages (`RentreePage`, `VieScolairePage`, `ConsoleEtablissementPage`,
et `ClassesPage` réécrite), un moteur de formulaire dynamique partagé
(`FormulaireBuilder`/`FormulaireDynamique`, réutilisé recrutement + actes académiques), le
téléchargement PDF+QR sur les tickets transport/cantine/billetterie, et un mode « scanner un
QR code » (API navigateur `BarcodeDetector`, sans nouvelle dépendance) sur `ValiderAccesPage`.
En vérifiant la concordance des rôles micro-jobs/marketplace avec la nouvelle règle
étudiant-only (UC-57/58), révélé et corrigé un vrai bug frontend antérieur à cette phase :
`MicroJobsPage.tsx` gate `estEleve` bloquait TOUS les élèves (y compris les futurs étudiants
seuls éligibles) et laissait TOUS les adultes accepter des offres — l'exact inverse de la
règle validée par l'utilisateur pour ce lot. Corrigé en exposant `est_etudiant` (calculé une
seule fois côté backend, `app.core.etudiant.est_etudiant`) sur `GET /me` et `GET /eleves/me`,
plutôt que de dupliquer un calcul de rôle/âge côté client. Un deuxième bug (introduit puis
corrigé dans la même session) : ajouter `est_etudiant` à `MeOut` sans construire le dict de
retour dans les DEUX endpoints qui répondent avec ce schéma (`/me` et
`/auth/change-password`, qui renvoyait l'objet ORM brut) cassait `change-password` en
`ResponseValidationError` — corrigé en factorisant `_construire_me_out()`, détecté par la
suite pytest avant tout commit. 175 tests toujours passants. Vérifié par `tsc -b` + `vite
build` (aucune erreur) après chaque lot. Détail complet dans `frontend/PROJECT_MAP.md`.
Prochaine étape : 7 (intégration et correction des écarts).

2026-09-26 (Phase 6, backend) — Étape 4 du lot Phase 6 : backend complet endpoint par
endpoint pour les 6 sous-lots (rentrée/vie scolaire, classes/console, recrutement dynamique,
actes dynamique, ticketerie QR, restriction étudiants) — voir détail dans
`backend/PROJECT_MAP.md`. 175 tests passants (31 nouveaux/réécrits), migration `0007`
appliquée et vérifiée (upgrade+downgrade) contre un vrai Postgres local. Correction UC-57
en cours de route sur arbitrage explicite de l'utilisateur : les adultes gardent l'accès
CLIENT (publier/payer un micro-job) mais perdent l'accès PRESTATAIRE (accepter/être payé),
désormais réservé aux étudiants — reverse une partie d'ADR-008 sans l'annuler entièrement
(les adultes restent clients). Prochaine étape : 6 (frontend).

2026-09-26 (Phase 6, ideation) — Nouveau lot proposé (pas encore validé) :
`docs/cahier-des-charges-refonte-admin-etablissement.md`, en réponse à une demande de
refonte du profil A+ (admin établissement) en 6 points : rentrée scolaire + « vie
scolaire » portable entre établissements (UC-39 à UC-42), classes enrichies avec année
académique et console de filtrage multi-modules (UC-43 à UC-46), recrutement et actes
académiques avec formulaire dynamique façon Google Forms (UC-47 à UC-53), ticketerie
unifiée avec QR codes (UC-54 à UC-56), micro-jobs/marketplace réservés aux étudiants
(UC-57 — **reverse la règle ADR-008** qui ouvrait les micro-jobs à tous les rôles adultes,
à confirmer avant code). Constat structurant : aucune notion d'année académique n'existe
dans le schéma actuel (`Classe` est une table perpétuelle) — devient une dimension de
premier ordre dès le Lot 6.2, dont dépendent 6.1 et indirectement 6.6. Priorisation
proposée : commencer par 6.2 (année académique + classes) puis 6.1 (rentrée/vie scolaire).
En attente de validation utilisateur avant diagrammes UML/contrat d'API/code.

2026-09-26 (Phase 5, frontend) — Frontend complet pour UC-23 à UC-38 : composant
`DataTable` générique réutilisable (`frontend/src/components/DataTable.tsx`), 3 pages
refondues (Établissements, Référentiels, Arbitrage micro-jobs — fin de la saisie manuelle
d'ID) et 4 nouvelles pages (Utilisateurs, Contenus pédagogiques, Événements, Journal
d'audit). En vérifiant en navigateur réel contre les données `seed_mega.py` déjà présentes
en local (6227 utilisateurs, jamais exploitées jusqu'ici faute de Postgres local
disponible dans les sessions précédentes), révélé et corrigé un vrai bug : `GET /me` et le
nouveau `GET /admin/utilisateurs` renvoyaient 500 sur tout compte seedé avec un e-mail
`.test` (validation Pydantic `EmailStr` trop stricte pour un champ d'affichage agrégeant
des milliers de comptes) — corrigé en repassant `AdminUtilisateurOut.email` en `str`
simple. Vérifié par `tsc -b`/`vite build` au vert et par des appels réels (navigateur +
curl) contre le backend réel : établissement suspendu/réactivé en masse (disparition/
réapparition confirmée dans l'annuaire public), référentiel validé en lot puis modifié en
ligne, compte suspendu puis bloqué sur un endpoint protégé puis réactivé — chaque action
retrouvée dans le journal d'audit. Détail complet dans `frontend/PROJECT_MAP.md`.
Prochaine étape : étape 7 (intégration et correction des écarts).

2026-09-26 (Phase 5, backend) — Cahier des charges validé (points `[Délégué]` confirmés),
diagrammes UML faits (`docs/diagrammes-uml-phase-5-admin-ministeriel.md`, contrat d'API
fusionné dans le même document sur demande explicite), **backend complet** pour UC-23 à
UC-38 : établissements enrichis (description + suspension d'homologation), référentiels
éditables/validables en masse par l'A++, files d'arbitrage micro-jobs enrichies (fin de la
saisie manuelle d'ID), supervision utilisateurs (recherche + suspension de compte),
supervision et modération de contenus pédagogiques (masquage non destructif), supervision
événements + annulation d'urgence, nouveau journal d'audit ministériel transversal.
Migration `0006` appliquée et vérifiée (upgrade+downgrade) contre un vrai Postgres local —
a aussi révélé et corrigé un vrai bug bloquant sur les migrations `0002`-`0005`, jamais
appliquées contre un Postgres réel avant cette session (`alembic_version` trop étroit).
163 tests passants au total (10 nouveaux), aucune régression. Détail complet dans
`backend/PROJECT_MAP.md`. Prochaine étape : frontend (DataTable générique + écrans).

2026-09-26 (encore plus tard, refonte admin ministériel) — Nouveau lot proposé (pas encore Phase 5 officielle, pas encore validé) : `docs/cahier-des-charges-refonte-admin-ministeriel.md`, en réponse à une demande de correction du profil A++ (admin ministériel) en 4 points (vitrine établissement sans photos/description, référentiels non gérables en masse, arbitrage micro-jobs par saisie manuelle d'ID sans file d'attente, aucune supervision transverse de la plateforme). Document d'ideation (pas un cas d'utilisation verrouillé) : analyse de solutions comparables (OpenEMIS, patterns DataTables, files d'arbitrage gig-economy), gaps identifiés, UC-23 à UC-38 proposés, priorisation P0/P1/P2, feuille de route en 7 lots (5.1 à 5.7) alignée sur le pipeline `lucio-dev`, risques (dont pagination serveur sur le plan Postgres gratuit et traçabilité des nouveaux pouvoirs de suspension/modération). En attente de validation utilisateur avant tout diagramme UML/contrat d'API/code — étape 1 du pipeline seulement.

2026-09-26 (encore plus tard, marketplace, frontend) — Étape 6 du lot Phase 4 : `frontend/src/pages/eleve/MarketplacePage.tsx` (élève : catalogue, publication, réservation/paiement Kkiapay, mes annonces, mes transactions) et `frontend/src/pages/admin_etablissement/MarketplaceAdminPage.tsx` (A+ : signalements, retrait, litige/reversement). En construisant la page A+, correction d'un vrai écart : le backend ne laissait pas l'A+ consulter le catalogue (RBAC élargi, test ajouté, 144 tests passants au total). Validé par `tsc -b` + `vite build`, pas par un parcours manuel en navigateur (aucun Postgres local dans cet environnement — même limite déjà acceptée pour la Phase 2/3). Détail complet dans `frontend/PROJECT_MAP.md`. Prochaine étape : 7 (intégration et correction des écarts, notamment le parcours manuel en navigateur dès qu'un Postgres est disponible).

2026-09-26 (encore plus tard, marketplace, e2e) — Étape 5 du lot Phase 4 : validation de bout en bout (`backend/tests/test_e2e_parcours_phase4_marketplace.py`, UC-20→21→22 dans l'ordre réel avec un seul jeu d'objets) et scan de sécurité de la méthode `lucio-dev` (bandit + pip-audit installés pour l'occasion : 0 problème sur le nouveau code, 2 CVE non bloquantes sur une dépendance transitive `ecdsa` déjà présente avant ce lot, jamais exercée car la plateforme signe en HS256). 143 tests passants au total, aucune régression. Détail complet dans `backend/PROJECT_MAP.md`. Prochaine étape : 6 (frontend), ou vérification de la migration `0004` contre un vrai Postgres avant tout déploiement.

2026-09-26 (encore plus tard, marketplace, backend) — Étape 4 du lot Phase 4 : backend complet pour UC-20/21/22 (`backend/app/modules/marketplace/`), migration `0004_marketplace.py`, webhook Kkiapay étendu. 11 nouveaux tests, 141 tests passants au total, aucune régression sur la suite existante. Arbitrage/reversement confiés à l'A+ de l'établissement (vendeur et acheteur toujours du même établissement, contrairement aux micro-jobs). Détail complet dans `backend/PROJECT_MAP.md`. Prochaine étape : 5 (validation de bout en bout, nécessite un vrai Postgres pour la migration).

2026-09-26 (encore plus tard, marketplace, contrat d'API) — Étape 3 du lot Phase 4 : contrat d'API complet dans `docs/contrat-api-phase-4-marketplace.md` (annonces UC-20, achat avec séquestre et litige UC-21/UC-22). Choix technique non repris à la demande de l'utilisateur (aucune nouvelle intégration : stack, séquestre Kkiapay et stockage LuluFiles réutilisés tels quels). Reversement au vendeur arbitré et exécuté par l'A+ de l'établissement (pas l'A++ comme pour les micro-jobs, UC-18) car vendeur et acheteur appartiennent toujours au même établissement dans ce flux. Prochaine étape : 4 (backend, endpoint par endpoint).

2026-09-26 (encore plus tard, marketplace) — Nouveau lot Phase 4 (marketplace étudiante), demandé par l'utilisateur, hors périmètre initial. Étapes 1-2 du pipeline `lucio-dev` validées : `docs/cas-utilisation-phase-4-marketplace.md` (UC-20 publier/consulter une annonce, UC-21 réserver/payer avec séquestre Kkiapay, UC-22 litige de réception ; trois décisions structurantes tranchées explicitement par l'utilisateur via AskUserQuestion — marketplace réservée aux élèves ≥16 ans du même établissement, paiement par séquestre) et `docs/diagrammes-uml-phase-4-marketplace.md` (UC32-38 + un diagramme de classes). Réutilise les mécanismes déjà validés (séquestre Kkiapay ADR-008, photos LuluFiles ADR-003/009) sans nouvelle intégration technique. Aucun code écrit à ce stade — étape 3 (choix technique/contrat d'API) reste à faire avant le backend.

2026-09-26 (encore plus tard) — Diagnostic et résolution de plusieurs échecs de déploiement Render successifs : région de la base Postgres à faire correspondre à celle du service web (l'URL interne `dpg-...-a` ne résout que dans la même région/compte), puis un vrai bug de migration (`0010_formulaires_llm.py` faisait `DROP TYPE statutsoumission` puis recréait aussitôt une table l'utilisant, échec `UndefinedObject`). Résolu en squashant les 22 migrations Alembic en une seule (`backend/alembic/versions/0001_schema_initial.py`, générée par autogenerate contre une base vide, upgrade+downgrade vérifiés) — détail dans `backend/PROJECT_MAP.md`.

2026-09-26 (plus tard) — Frontend Phase 2/3 complet (étape 6 du pipeline) pour 8 des 9 UC : messagerie (UC-13, avec modération A+), El Professor (UC-14, intégré à `CoursDetailPage`), cours en direct (UC-16), transport/cantine (UC-11/12), billetterie (UC-17), micro-jobs+arbitrage (UC-18). UC-19 (visites 3D/drone) volontairement laissé en teaser « Bientôt disponible » sur la landing page — décision explicite de l'utilisateur, le choix technique de la visite 3D n'a pas encore été arbitré. Deux ajouts backend mineurs livrés avec ce lot pour rendre l'UI possible : `InscriptionAvecEleveOut.eleve_utilisateur_id` (bouton « Contacter mon enfant ») et enrichissement des schémas messagerie (`classe_niveau`, `autre_participant_*`, `auteur_nom`/`prenom`, calculés côté routeur car dépendants du lecteur — jamais des `@property` SQLAlchemy). Vérifié par `tsc -b`, `vite build` et la suite pytest complète (124/124) — pas encore par un parcours manuel en navigateur rôle par rôle comme pour la Phase 1 (voir Limites dans `frontend/PROJECT_MAP.md`), à faire avant mise en production. Détail complet dans `frontend/PROJECT_MAP.md`.

2026-09-26 — Ajout de `frontend/netlify.toml` (Netlify comme deuxième option de déploiement frontend, en secours de Vercel — voir ADR-006 addendum pour la limite de crédits Netlify à connaître avant d'activer son auto-déploiement). Corrigé au passage un bug latent trouvé en écrivant cette config : `vercel.json` n'avait pas de repli SPA, recharger une route imbriquée (React Router) renvoyait un 404 — corrigé dans `vercel.json` et `netlify.toml`. Egalement corrigé `ModuleNotFoundError: No module named 'app'` au démarrage sur Render : `startCommand` appelait `alembic`/`uvicorn` comme scripts installés, qui n'ajoutent pas le répertoire courant à `sys.path` sur Linux (invisible en dev Windows) — passage à `python -m alembic`/`python -m uvicorn`, plus `prepend_sys_path = .` dans `alembic.ini` en filet de sécurité.

2026-09-25 — Finalisation du déploiement Render/Vercel pour des comptes **gratuits** + mise en place du CI/CD (voir ADR-006 addendum). `render.yaml` : `DATABASE_URL` codée en dur avec un vrai mot de passe dans un commit précédent, corrigée en `fromDatabase` (Blueprint `databases:`) — voir l'avertissement de rotation en tête de `docs/deploiement-render-vercel.md`. Casier judiciaire déplacé du disque local (indisponible sur le plan gratuit) vers un stockage chiffré (Fernet) en base (`VerificationCasierJudiciaire.contenu_chiffre`, migration `0022`). Ajout de `.github/workflows/backend-ci.yml` et `frontend-ci.yml` (tests/lint/build sur chaque push/PR, ne déploient rien). Corrigé au passage un bug latent (`HTTP_422_UNPROCESSABLE_CONTENT`, constante inexistante dans la version de Starlette utilisée, présent dans 7 routers) qui faisait échouer silencieusement toute réponse 422 explicite. 124 tests passants (backend), lint + build frontend au vert.

2026-09-25 (plus tôt) — Phase 2/3 : backend complet pour les 9 UC (UC-11 à UC-19) et validation de bout en bout (`test_e2e_parcours_phase2_3.py`), endpoint par endpoint avec tests immédiats comme en Phase 1. Webhook Kkiapay extrait de `actes/` vers un module `paiements/` partagé (Phase 1 + Phase 2/3, un seul webhook pour tout le compte). Deux corrections apportées au contrat en cours d'implémentation : arbitrage micro-jobs confié à l'A++ (pas "l'A+ de l'établissement du prestataire", qui n'existe pas pour un Tuteur prestataire), et ajout de `DELETE /messages/{id}` (masquage non destructeur, absent du premier jet). 120 tests passants. Par ailleurs, refonte du design system frontend vers une identité institutionnelle État béninois (ADR-007) — voir `frontend/PROJECT_MAP.md`. Landing page enrichie d'une scène 3D (étoiles Three.js + objets CSS flottants) et la vitrine établissements déportée sur un annuaire public dédié avec photos (ADR-009).
