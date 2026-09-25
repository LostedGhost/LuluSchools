# Suivi de projet — LuluSchools

Copier ce fichier au démarrage du projet et cocher au fur et à mesure des validations. Chaque case cochée correspond à un artefact réellement produit et validé, pas juste "commencé". Méthode : pipeline spec-first `lucio-dev`.

- [x] **1. Cas d'utilisation** — liste complète, validée explicitement (Phase 1 — voir `docs/cas-utilisation-phase-1.md`)
- [x] **2. Diagrammes UML** — diagramme de cas d'utilisation + diagramme de classes, validés — voir `docs/diagrammes-uml-phase1.md`
- [x] **3. Choix technique et contrat d'API** — stack retenue et contrat d'API validés — voir `README.md`, `docs/choix-technique-phase1.md`, `docs/contrat-api-phase1.md`, `docs/adr/`
- [x] **4. Backend** — tous les modules Phase 1 faits et testés (identité, établissements, inscriptions, recrutement/contrats, pédagogie, évaluations, actes) — 68 tests passants, dont le mot de passe temporaire réellement appliqué côté serveur. Matricule élève au format officiel (universitaire verrouillé par l'utilisateur, EP/ES proposé dans le même esprit — voir UC-03). Notation/correction IA multi-appels (candidatures, devoirs) exécutée en arrière-plan (`BackgroundTasks`), génération de quiz (un seul appel) reste synchrone — voir ADR-005
- [x] **5. Validation complète du backend** — scénario de bout en bout automatisé (`tests/test_e2e_parcours_complet.py`) rejouant UC-01 à UC-10 dans l'ordre réel d'usage, avec les mêmes objets circulant d'un module à l'autre. A révélé et corrigé un vrai bug (chemin du stockage du casier judiciaire mal interprété sous Windows). Connectivité réelle testée avec les vraies clés : **Brevo** (email réel envoyé, a nécessité d'autoriser l'IP sortante dans le dashboard Brevo), **FreeLLM** et **LuluFiles** OK. **Kkiapay** non testable en conditions réelles depuis le backend seul : l'intégration repose sur un widget côté client (frontend, pas encore construit) + un webhook — aucun appel sortant du backend vers Kkiapay n'existe à tester (voir `docs/contrat-api-phase1.md`) ; à valider lors de l'intégration frontend (étape 7)
- [x] **6. Frontend** — **les 5 rôles de la Phase 1 construits et testés en navigateur réel contre le backend réel** (pas de mocks, voir `frontend/PROJECT_MAP.md`) : Tuteur, Élève, Enseignant, A+ (admin établissement), A++ (admin ministériel). Boucle complète rejouée manuellement de bout en bout : compte tuteur → inscription → validation A+ → matricule élève → cours/quiz IA/devoir corrigé par IA → bulletin ; compte enseignant → candidature → notation IA (échec observé et corrigé manuellement) → contrat créé par l'A+ → signature par tracé canvas → publication de cours ; établissement créé par l'A++ → référentiel de coefficient. A révélé et corrigé 3 vrais bugs backend (`DocumentCandidatureOut`/`ContratOut` incomplets, route de listing de candidatures manquante) et 1 bug frontend (mismatch de valeur d'enum `tirage_sort`). Limites connues (non bloquantes) : pas de vue A+ pour proposer un référentiel, paiement Kkiapay non cliqué en conditions réelles (exécution financière hors périmètre d'un test automatisé), pas de tests automatisés frontend — voir `frontend/PROJECT_MAP.md`.
- [~] **7. Intégration** — de facto largement acquise : le frontend n'a jamais utilisé de mocks, connecté au backend réel dès le départ pour les 5 rôles, écarts corrigés au fil de l'eau. Reste un flux non vérifié en conditions réelles : le paiement Kkiapay pour un acte payant (widget implémenté, mais l'exécution d'une transaction réelle est hors périmètre d'un test automatisé — voir garde-fous de sécurité).
- [ ] **8. Déploiement** — configs prêtes (`render.yaml` pour le backend, `frontend/vercel.json` pour le frontend, voir ADR-006 et `docs/deploiement-render-vercel.md`), plan VPS initial abandonné. Reste à exécuter réellement : créer les comptes/services Render et Vercel, renseigner les secrets, seed du premier compte A++, mise à jour du webhook Kkiapay — étapes qui nécessitent un accès humain aux dashboards concernés.

## Cadrage verrouillé

- Portage : mandat ministériel officiel (Bénin). A++ = acteur gouvernemental réel.
- Zone V1 : Bénin — conformité suivie via le référentiel loi n° 2017-20 (skill `droit-numerique-benin`).
- Paiement / séquestre : Kkiapay (agrégateur mobile money/carte).
- Phasage MVP : Phase 1 (socle identité/inscriptions/contrats/cours/devoirs/moyennes) → Phase 2 (réclamations/actes payants/tickets/messagerie/**agent IA "El Professor"** — assistant pédagogique conversationnel qui explique les cours à l'élève et oriente chaque acteur selon son profil, idée de l'utilisateur, volontairement hors périmètre Phase 1 pour ne pas retarder la finalisation du MVP) → Phase 3 (vidéo/live/billetterie/micro-jobs+séquestre/3D).

## Phases 2 et 3 — pipeline redémarré à l'étape 1

Le backend Phase 1 (UC-01 à UC-10) est complet et testé (75 tests). L'utilisateur a demandé de finaliser le backend sur l'intégralité de sa vision du projet, toutes phases confondues — ce qui rouvre le pipeline `lucio-dev` à l'étape 1 pour les Phases 2 et 3, qui n'avaient jusqu'ici qu'une ligne de cadrage (`Phasage MVP` ci-dessous), aucun cas d'utilisation détaillé.

- [x] **1. Cas d'utilisation (Phases 2 et 3)** — **validé le 2026-09-25** dans `docs/cas-utilisation-phase-2-3.md` (UC-11 à UC-19 : tickets transport/cantine, messagerie, assistant IA "El Professor", vidéo/podcast, cours en direct, billetterie, micro-jobs+séquestre, visites 3D/drone). L'utilisateur a tranché UC-13 (DM adulte↔élève interdit, restreint au groupe de classe) et délégué l'arbitrage de tous les autres points ouverts (voir [[feedback-legal-autonomy]], étendue aux décisions structurantes). 2 points restent de vrais blocages administratifs hors logiciel (âge minimum micro-job UC-18, autorisation de vol drone UC-19), traités par exclusion/attestation en attendant, non bloquants pour la suite du pipeline.
- [x] **2. Diagrammes UML (Phases 2 et 3)** — diagramme de cas d'utilisation (UC17-UC31) + 4 diagrammes de classes par domaine (tickets/billetterie, messagerie/El Professor, contenu enrichi/live/visites, micro-jobs) — voir `docs/diagrammes-uml-phase2-3.md`. Dérivés strictement des UC validés, aucune nouvelle règle métier introduite. 3 points techniques (pas métier) reportés à l'étape 3 : séquestre Kkiapay, infra live, hébergement vidéo.
- [~] **3. Choix technique et contrat d'API (Phases 2 et 3)** — en cours.
- [ ] **4. Backend (Phases 2 et 3)** — non démarré.
- [ ] **5. Validation complète du backend (Phases 2 et 3)** — non démarré.
- [ ] **6. Frontend (Phases 2 et 3)** — non démarré.
- [ ] **7. Intégration (Phases 2 et 3)** — non démarré.
- [ ] **8. Déploiement (Phases 2 et 3)** — non démarré.

## Notes / écarts assumés

- **Plan LuluFiles gratuit ("Lancement")** : 5 Go de transfert/mois et 2 Mo/s de bande passante partagés par tout le compte. Choix assumé par l'utilisateur pour la Phase 1 pilote ; passage à un plan payant prévu au besoin, à réévaluer avant la Phase 2/3 (voir `docs/adr/ADR-003-stockage-fichiers-lulufiles.md`) — redevient un point bloquant concret dès UC-15 (vidéo pédagogique), voir `docs/cas-utilisation-phase-2-3.md`.
