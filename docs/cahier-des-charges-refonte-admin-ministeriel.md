# Refonte du portail Admin Ministériel (A++) — Cahier des charges

> **Version** : 1.1 | **Date** : 2026-09-26 | **Statut** : **Validé** (y compris tous les points `[Délégué]`, confirmés tels qu'écrits) — étape 1 close, diagrammes UML faits (`docs/diagrammes-uml-phase-5-admin-ministeriel.md`, contrat d'API fusionné dans ce même document à la demande explicite de l'utilisateur), passage direct au backend

Ce document fait désormais foi comme cas d'utilisation verrouillé pour ce lot (numérotation UC-23 à UC-38 conservée). Les décisions de structuration ambiguës (pas de règle métier explicite du cahier des charges Phase 1/2/3) ont été tranchées de façon autonome, marquées **[Délégué]**, et validées sans changement.

---

## 1. Problème & pitch

### 1.1 Constat

Le rôle **A++ (admin ministériel)** existe depuis la Phase 1 mais reste le parent pauvre du frontend : 3 pages isolées (`EtablissementsPage`, `ReferentielsPage`, `MicroJobsArbitragePage`) pendant que les A+ ont un tableau de bord riche. Or le backend a été audité et corrigé le 2026-09-26 (« Refonte RBAC ») précisément pour que l'A++ ait accès à la quasi-totalité de la portée établissement — ce potentiel n'est exploité par aucune interface aujourd'hui. C'est un décalage backend/frontend, pas un manque de capacité technique.

Quatre lacunes concrètes ont été identifiées :
1. La vitrine établissement du Ministère est un simple formulaire + liste texte, sans aucune des photos/descriptions que l'annuaire public (`/etablissements`) affiche déjà pour le même établissement.
2. Les référentiels de coefficients sont une liste de cartes non triable, non filtrable, sans action groupée — ingérable à l'échelle nationale (des dizaines de niveaux × matières × établissements proposants).
3. L'arbitrage des micro-jobs se fait par **saisie manuelle d'un identifiant technique** (aucune file d'attente visible) — déjà noté comme limite connue dans `frontend/PROJECT_MAP.md`.
4. Le Ministère n'a aucune vue transversale sur ce qui circule réellement sur la plateforme (utilisateurs, cours, devoirs, événements) — il ne peut « voir » que ce que les 3 pages existantes exposent.

### 1.2 Hypothèses de départ [Délégué]

- Ce lot est traité **après** les autres profils déjà en correction (cadence « profil par profil » déjà adoptée) — mais il peut être livré en plusieurs sous-lots indépendants (voir § 6), pas d'un bloc.
- « Voir tout ce qui transite » (point 4) est interprété comme un **pouvoir de supervision en lecture + actions de modération ciblées** (suspendre un compte, masquer un contenu signalé, annuler un événement en urgence), **pas** un accès disposant de tous les droits d'un A+ sur chaque établissement (ex. créer des classes, gérer la paie, etc.) — ce serait une confusion de rôle, pas une supervision.
- Aucune de ces fonctionnalités n'introduit de flux d'argent nouveau ni de modèle économique : LuluSchools est un mandat ministériel, pas un produit commercial. La section « business model » du gabarit habituel est donc remplacée par une section **Gouvernance & Exploitation** (§ 8).

### 1.3 Pitch

Transformer le portail A++ d'un guichet à 3 formulaires en un **centre de pilotage national** : une vitrine établissement complète, une gouvernance des référentiels en datatable (tri/filtre/recherche/actions groupées), une vraie file d'arbitrage (plus de saisie d'ID à l'aveugle), et un panneau de supervision transverse (utilisateurs, contenus, événements) avec journal d'audit — pour que le Ministère pilote le réseau au lieu de simplement l'alimenter.

---

## 2. Analyse de l'existant et de solutions comparables

Recherche menée sur des systèmes comparables (EMIS nationaux, patterns d'admin datatable, files d'arbitrage gig-economy) pour ne pas réinventer un pattern déjà résolu ailleurs.

| Référence | Ce qu'elle fait bien | Angle mort par rapport à notre besoin |
|---|---|---|
| **OpenEMIS** (EMIS national, utilisé par plusieurs ministères, dont en Afrique) | Cœur du produit : parcourir/filtrer **tous** les établissements d'un pays depuis un seul tableau de bord, stats par région/secteur/type, alimente des indicateurs nationaux. | Pensé pour la donnée statistique (effectifs, présence), pas pour l'arbitrage de litiges ni la modération de contenu pédagogique. |
| **Patterns Bootstrap DataTables** (admin panels génériques) | Tri, pagination, recherche, densité d'affichage, édition en ligne quand le produit l'exige — « la meilleure table est celle qui colle au workflow de l'utilisateur ». | Ne dit rien sur *quelles* actions groupées ont du sens pour un régulateur (ce n'est pas un CRM générique). |
| **Files d'arbitrage gig-economy** (ex. patterns de dispute queue étudiés : table listant litige/montant/parties/ancienneté plutôt que recherche par ID) | Le constat exact qui nous concerne : *« les arbitres doivent aujourd'hui ouvrir chaque dossier pour trouver les litiges »* — un problème identique à notre `MicroJobsArbitragePage` actuelle. La solution retenue ailleurs : une file unique avec le contexte visible avant décision. | — |

### 2.1 Gaps stratégiques retenus

1. **Asymétrie de vitrine** : le public voit mieux un établissement que le Ministère qui l'a homologué.
2. **Pas de socle de tableau générique** : chaque nouvelle liste (référentiels, utilisateurs, cours...) recommencerait le même travail de tri/filtre/pagination si on ne factorise pas un composant réutilisable dès ce lot.
3. **Arbitrage à l'aveugle** : décision prise sans file d'attente ni contexte pré-chargé (montant, motif, historique des parties).
4. **Portée backend inexploitée** : le RBAC élargi de l'A++ (2026-09-26) n'a aucune UI de consommation transverse — aucun endpoint global (utilisateurs, cours, événements) n'existe non plus côté backend, seulement des listes scopées par établissement/classe.
5. **Aucune trace des décisions ministérielles** : ni les validations de référentiel, ni les arbitrages, ni une future suspension de compte ne sont journalisés nommément — un vrai mandat public devrait pouvoir être audité.

---

## 3. Solution proposée

### 3.1 Description générale

Un socle commun — un **composant DataTable générique** (tri, pagination serveur, filtre par colonne, recherche dynamique debouncée, sélection multi-ligne + barre d'actions groupées contextuelle, état vide/chargement/erreur conforme au design system) — puis quatre familles d'écrans qui le consomment :

- **Gouvernance active** (le Ministère décide) : Établissements, Référentiels, Arbitrage micro-jobs.
- **Supervision passive** (le Ministère surveille et intervient au besoin) : Utilisateurs, Contenus pédagogiques, Événements.

### 3.2 Avantage structurant

Construire le composant DataTable une fois, bien, avec les checklists UX/sécurité du pipeline `lucio-dev`, plutôt que de le dupliquer à chaque écran (le référentiel d'aujourd'hui, les utilisateurs demain) — c'est l'investissement qui rend tout le reste rapide à livrer ensuite, y compris pour d'autres profils plus tard **[Délégué : le composant est conçu pour être réutilisable par les A+ dans un futur lot, mais ce lot ne retouche que les écrans A++ — pas de dérive de périmètre vers d'autres profils maintenant]**.

### 3.3 Fonctionnalités clés

| Priorité | Fonctionnalité | Bénéfice |
|---|---|---|
| **P0** | Composant `DataTable` générique (tri/pagination/filtre/recherche/sélection/actions groupées) | Socle réutilisable, condition des 5 écrans suivants |
| **P0** | Établissements enrichis (photos + description + fiche détaillée, dans le même style que `/etablissements` public) | Corrige la lacune #1 signalée |
| **P0** | Référentiels en DataTable + édition directe par A++ + validation groupée de propositions + normalisation niveau/matière | Corrige la lacune #2, gouvernance nationale utilisable à l'échelle |
| **P0** | File d'arbitrage micro-jobs (contestations en attente + missions à reverser, avec contexte complet, plus de saisie d'ID) | Corrige la lacune #3, aligné avec le pattern « dispute queue » observé ailleurs |
| **P1** | Supervision Utilisateurs (liste nationale, recherche, filtre par rôle/établissement, suspension/réactivation de compte) | Première brique de la supervision transverse demandée (#4) |
| **P1** | Journal d'audit ministériel (qui a validé/arbitré/suspendu quoi, quand, pourquoi) | Accompagne *dès* la première action destructrice (suspension) — pas reporté en fin de lot |
| **P1** | Supervision Contenus pédagogiques (cours/devoirs, tous établissements, filtrable, action de masquage sur signalement) | Complète #4 côté contenu |
| **P2** | Supervision Événements (billetterie, tous établissements, annulation d'urgence nationale) | Complète #4 côté événementiel |
| **P2** | Tableau de bord KPI enrichi (comptes actifs par rôle, volume de contenu, missions en cours, transactions marketplace) | Vue d'ensemble pour le pilotage, consomme les données déjà collectées par les lots précédents |

---

## 4. Cas d'utilisation proposés (brouillon — à valider)

Numérotation à la suite d'UC-22 (Phase 4, marketplace).

### 4.1 Établissements & Homologations

- **UC-23** — En tant qu'A++, je veux voir chaque établissement avec ses photos et sa description (comme sur l'annuaire public), afin d'homologuer en connaissance visuelle et pas seulement administrative.
  - Règle : réutilise `Carousel`/`photosPubliques()` déjà existants ; ajoute un champ `description` (texte libre, optionnel) sur `Etablissement` — **absent aujourd'hui du modèle**, nouvelle migration nécessaire.
- **UC-24** — En tant qu'A++, je veux gérer (ajouter/retirer) les photos et la description de **n'importe quel** établissement, pas seulement son A+, afin de pouvoir modérer un contenu inapproprié signalé au niveau national.
  - **[Délégué]** : élargit un pouvoir aujourd'hui réservé à l'A+ (`PhotosEtablissementManager`) — cohérent avec le principe de supervision nationale, sans retirer le droit de l'A+ sur son propre établissement.
- **UC-25** — En tant qu'A++, je veux consulter la liste des établissements en datatable (recherche par nom/code, filtre par type/statut/région si disponible, tri par nb d'élèves/classes), afin de retrouver un établissement en quelques secondes sur un réseau à vocation nationale (potentiellement des centaines d'entrées).
- **UC-26** — En tant qu'A++, je veux sélectionner plusieurs établissements et leur appliquer une action groupée (ex. exporter en CSV, ou changer un statut en masse), afin de gagner du temps sur des opérations répétitives.
  - **[Délégué]** : périmètre exact des actions groupées établissement laissé ouvert à discussion — proposition de départ : export CSV (sans risque) + suspension groupée d'homologation (avec confirmation + motif obligatoire).

### 4.2 Référentiels de coefficients

- **UC-27** — En tant qu'A++, je veux voir tous les référentiels (nationaux + propositions d'A+) dans une datatable triable/filtrable (par statut, niveau, matière, établissement proposant), afin de gouverner la pondération nationale sans faire défiler des dizaines de cartes.
- **UC-28** — En tant qu'A++, je veux modifier directement le coefficient d'un référentiel déjà validé (sans repasser par un cycle proposition→validation, réservé aux A+), afin de corriger une erreur ou ajuster une politique nationale immédiatement.
  - Règle : nouvel endpoint `PATCH /referentiels-coefficients/{id}` réservé A++, distinct du flux `proposition`/`valider` qui reste la seule voie pour un A+.
- **UC-29** — En tant qu'A++, je veux sélectionner plusieurs propositions en attente et les valider en un seul geste (ex. plusieurs propositions cohérentes soumises la même semaine par des A+ différents), afin d'accélérer la gouvernance sans cliquer une à une.
- **UC-30** — En tant qu'A++, je veux que les champs niveau/matière proposent une liste de valeurs déjà existantes (autocomplétion sur les valeurs distinctes déjà en base) plutôt qu'un champ libre non contrôlé, afin d'éviter les doublons quasi-identiques (« CE1 » vs « ce1 »).
  - **[Délégué]** : autocomplétion côté client à partir des valeurs déjà chargées (pas de nouvel endpoint ni de table de taxonomie figée — reste un champ texte libre, juste guidé) ; une vraie contrainte d'énumération serait une migration de données plus lourde (les niveaux réels varient EP/ES/UP, cf. taxonomie de `seed_mega.py`), hors périmètre de ce lot.

### 4.3 Arbitrage micro-jobs

- **UC-31** — En tant qu'A++, je veux voir la liste de toutes les contestations en attente (motif, montant, mission, client, prestataire, ancienneté), afin de savoir ce qu'il reste à trancher sans connaître d'identifiant à l'avance.
  - Règle : nouvel endpoint `GET /contestations-micro-job?statut=en_attente`, réservé A++, avec `ContestationMicroJobOut` enrichi (mission, offre, noms des parties — même pattern que l'enrichissement déjà fait sur `CandidatureOut` en Phase 1).
- **UC-32** — En tant qu'A++, je veux cliquer sur une contestation pour ouvrir un panneau de détail (motif complet, historique de la mission, montant séquestré) et **seulement alors** trancher (accepter/rejeter avec motif), afin de décider en connaissance de cause plutôt qu'à l'aveugle sur un ID collé.
  - C'est la reformulation exacte du point 3 demandé : « ce n'est qu'en cliquant pour arbitrer qu'on verra les informations ».
- **UC-33** — En tant qu'A++, je veux voir la liste des missions validées en attente de reversement au prestataire (avec montant et contact mobile money déjà connu du prestataire), afin de traiter le séquestre sans ressaisir d'identifiant.
  - Règle : nouvel endpoint `GET /missions-micro-job?statut=validee&reversee=false`, réservé A++.

### 4.4 Supervision transverse (nouveau)

- **UC-34** — En tant qu'A++, je veux consulter la liste nationale des utilisateurs (tous rôles), filtrable par rôle/établissement/statut de compte et recherchable par nom/e-mail/matricule, afin de retrouver un compte sans devenir A+ de chaque établissement.
  - Règle : nouvel endpoint paginé `GET /admin/utilisateurs`, réservé A++, champs strictement nécessaires (jamais mot de passe, jamais casier judiciaire) — réutilise le pattern de recherche par nom déjà livré pour l'affectation enseignant↔classe.
- **UC-35** — En tant qu'A++, je veux suspendre (et réactiver) un compte utilisateur avec un motif obligatoire, afin de neutraliser un compte problématique signalé sans attendre une procédure disciplinaire complète côté établissement.
  - Règle : nouveau champ `actif: bool` sur `Utilisateur` (absent aujourd'hui) + `POST /admin/utilisateurs/{id}/suspendre` / `/reactiver`, motif obligatoire, `get_current_active_user` doit désormais aussi vérifier `actif`.
- **UC-36** — Chaque action listée en UC-24, UC-28, UC-35 (et les suivantes) doit être journalisée (qui, quoi, quand, motif) dans un journal d'audit consultable par l'A++, afin qu'un mandat public reste traçable.
  - Règle : nouvelle table `JournalAuditMinisteriel` (acteur, action, cible, motif, horodatage) + endpoint de lecture paginé/filtrable — **livré avec le premier pouvoir destructeur (UC-35), pas reporté en fin de projet**.
- **UC-37** — En tant qu'A++, je veux consulter la liste agrégée des cours/devoirs publiés sur la plateforme (filtrable par établissement/enseignant/matière) et pouvoir masquer un contenu signalé, afin d'exercer une supervision pédagogique nationale.
- **UC-38** — En tant qu'A++, je veux consulter la liste agrégée des événements (billetterie) tous établissements et pouvoir en annuler un en urgence (remboursement automatique déjà géré par le module existant), afin de pouvoir agir vite en cas de nécessité nationale (sécurité, santé publique).

---

## 5. Priorisation (rappel synthétique)

| Lot | Contenu | Priorité |
|---|---|---|
| 5.1 | DataTable générique + Établissements enrichis | P0 |
| 5.2 | Référentiels v2 (datatable + édition directe + validation groupée) | P0 |
| 5.3 | Arbitrage micro-jobs v2 (files de contestations + reversements) | P0 |
| 5.4 | Supervision Utilisateurs + suspension/réactivation + journal d'audit | P1 |
| 5.5 | Supervision Contenus pédagogiques | P1 |
| 5.6 | Supervision Événements | P2 |
| 5.7 | Tableau de bord KPI enrichi | P2 |

---

## 6. Feuille de route (alignée sur le pipeline `lucio-dev`)

Chaque lot ci-dessus rejoue les 8 étapes déjà appliquées aux Phases 1/2/3/4 (cas d'utilisation → UML → contrat d'API → backend endpoint par endpoint avec tests/doc immédiats → validation de bout en bout → frontend → intégration → déploiement), **verrouillé lot par lot** plutôt qu'en un seul bloc — même discipline que la cadence « profil par profil » déjà adoptée pour cette série de corrections.

1. **Validation de ce cahier des charges** (ce document) — arbitrer les points `[Délégué]`, ajuster/valider les UC-23 à UC-38.
2. **Lot 5.1 → 5.3** (P0) : diagrammes UML + contrat d'API pour les 3 lots à la fois (ils partagent le composant DataTable), puis backend/frontend lot par lot.
3. **Lot 5.4** (P1) : introduit la suspension de compte et le journal d'audit — traité à part car il touche `get_current_active_user` (impact transverse à tous les rôles, à re-tester en régression sur toute la suite existante).
4. **Lots 5.5 → 5.7** (P1/P2) : supervision contenu/événements/KPI, une fois la mécanique de liste+action groupée éprouvée sur les lots précédents.
5. Déploiement uniquement après validation de bout en bout de chaque lot (pas en parallèle d'un lot encore instable).

---

## 7. Risques

| # | Risque | Catégorie | Probabilité | Impact | Mitigation |
|---|---|---|---|---|---|
| R1 | Requêtes non paginées côté serveur sur les nouvelles listes globales (utilisateurs/cours) saturent le plan Postgres gratuit (déjà signalé comme limite dans ADR-006) | Technique | Moyenne | Moyen | Pagination serveur obligatoire dès le contrat d'API, `limit` plafonné côté serveur — même pattern déjà appliqué à l'annuaire public établissements |
| R2 | Une liste nationale d'utilisateurs augmente la surface de risque en cas de compromission du seul compte A++ | Sécurité / légal (loi n°2017-20, APDP) | Faible | Élevé | N'exposer que les champs strictement nécessaires (jamais mot de passe/casier judiciaire), 2FA hors périmètre actuel mais à envisager séparément, journal d'audit sur les actions sensibles |
| R3 | Pouvoirs de suspension/masquage/annulation exercés sans motif ni traçabilité | Gouvernance | Moyenne | Élevé | Motif obligatoire sur chaque action destructrice + journal d'audit livré **avec** la première de ces actions (UC-35/UC-36), pas après |
| R4 | Dérive de périmètre (le composant DataTable générique tente de couvrir tous les cas dès le lot 5.1 et retarde tout) | Produit / calendaire | Moyenne | Moyen | Construire le composant pour les besoins réels des lots 5.1-5.3 uniquement ; l'étendre plus tard si un besoin concret apparaît, jamais par anticipation |
| R5 | Confusion de rôle : la supervision A++ empiète sur la gestion opérationnelle réservée à l'A+ (ex. modifier une classe) | Produit | Faible | Moyen | Cadrage explicite en §1.2 : supervision + actions de modération ciblées, jamais les droits de gestion complets d'un A+ |

---

## 8. Gouvernance & exploitation (remplace la section « modèle économique »)

LuluSchools opère sous mandat ministériel, pas de flux de revenu à concevoir pour ce lot. Points d'exploitation à noter :
- Coût d'infrastructure marginal (les nouveaux endpoints réutilisent le backend/DB déjà provisionnés sur Render, plan gratuit — voir ADR-006) ; seul R1 ci-dessus appelle une vigilance de pagination, pas un changement de plan.
- Responsabilité de maintenance inchangée (même équipe, même stack, pas de nouvelle intégration tierce).
- Les nouveaux pouvoirs (suspension, masquage, annulation) sont des capacités **d'État régulateur**, pas des fonctionnalités commerciales — leur légitimité doit être traçable (journal d'audit, R3) plutôt que rentabilisée.

---

## 9. Annexes

### 9.1 Glossaire
- **A++** : Admin Ministériel (`RoleUtilisateur.ADMIN_MINISTERIEL`), portée nationale.
- **A+** : Admin Établissement (`RoleUtilisateur.ADMIN_ETABLISSEMENT`), portée limitée à son établissement.
- **Séquestre** : montant bloqué chez Kkiapay jusqu'à validation/arbitrage (ADR-008).
- **DataTable** : composant frontend générique (tri, pagination, filtre, recherche, sélection multiple, actions groupées).

### 9.2 Sources consultées
- [OpenEMIS (Wikipedia)](https://en.wikipedia.org/wiki/OpenEMIS)
- [OpenEMIS — Education Management Information System (UNESCO)](https://unesdoc.unesco.org/ark:/48223/pf0000214777)
- [Bootstrap Table Guide and Best Bootstrap Table Examples (Flatlogic)](https://flatlogic.com/blog/bootstrap-table-guide-and-best-bootstrap-table-examples/)
- [Add arbiter dispute queue page (pattern de file d'arbitrage observé)](https://github.com/shakurJJ/chainsettle-frontend/issues/69)
- Contexte interne : `frontend/PROJECT_MAP.md`, `backend/PROJECT_MAP.md` (section « Refonte RBAC », 2026-09-26), code actuel de `EtablissementsPage.tsx`, `ReferentielsPage.tsx`, `MicroJobsArbitragePage.tsx`, `micro_jobs/router.py`, `evaluations/router.py`, `identite/models.py`.
