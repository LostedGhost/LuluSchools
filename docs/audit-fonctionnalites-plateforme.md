# Audit des fonctionnalités — LuluSchools (2026-09-26)

Photographie de l'état réel de la plateforme après fusion du volet Professeur/Élève-Tuteur
(UC-23 à UC-38) avec le lot admin établissement (UC-39 à UC-58). Compilé à partir de
[backend/PROJECT_MAP.md](../backend/PROJECT_MAP.md), [frontend/PROJECT_MAP.md](../frontend/PROJECT_MAP.md)
et des cahiers des charges validés ; aucune fonctionnalité listée ici n'est déduite, tout est
vérifiable dans le code ou les tests cités.

## 1. Chiffres clés

| | |
|---|---|
| Cas d'utilisation couverts | 58 (UC-01 à UC-58) |
| Rôles permanents | 5 (Tuteur, Élève/Étudiant, Enseignant, Admin établissement A+, Admin ministériel A++) |
| Rôles temporaires | 3 (Contrôleur/Ticketeur, Parrain d'événement, Prestataire micro-job) |
| Modules backend | 21 (`app/modules/*`) |
| Tests backend passants | 239 (aucune régression) |
| Validation frontend | `tsc -b` + `vite build` + `oxlint` au vert ; 4 des 6 phases rejouées en navigateur réel (backend réel, sans mocks) |
| Paiement | Kkiapay (widget + webhook unique pour tout le compte, ADR-008) |
| IA | FreeLLM, API compatible OpenAI (ADR-002) — notation, quiz, correction, El Professor (4 personas), résumés, digest |
| Stockage fichiers | LuluFiles (ADR-003) — tout document sauf casier judiciaire (chiffré Fernet, stocké en base, Art. 395) |
| Cadrage légal | Loi n° 2017-20 (Code du numérique béninois) — suivi article par article |

## 2. Rôles et parcours

- **A++ (admin ministériel)** — supervision nationale : création d'établissements, référentiels
  de coefficients, arbitrage micro-jobs, supervision transverse (utilisateurs/cours/devoirs/
  événements), journal d'audit.
- **A+ (admin établissement)** — gestion opérationnelle d'un établissement : classes/rentrées,
  recrutement, vie scolaire, console multi-modules, ticketerie, marketplace/actes.
- **Enseignant** — cours, quiz, devoirs, vie scolaire de ses classes, El Professor (conseil
  éducatif), sessions live avec tableau collaboratif.
- **Élève/Étudiant** — parcours pédagogique complet, El Professor, marketplace/micro-jobs
  (réservés aux étudiants majeurs UP), passeport de compétences.
- **Tuteur** — suivi de ses enfants (vie scolaire, devoirs, bulletins), Coffre-fort familial,
  Radar familial, El Professor Tuteur/Famille, résumés de session live.
- **Rôles temporaires** — Contrôleur/Ticketeur (validation tickets/billets), Parrain
  d'événement (délégation sans nouveau rôle RBAC), Prestataire micro-job (étudiant uniquement).

## 3. Modules, par domaine

### 3.1 Identité & comptes
- Inscription tuteur/enseignant avec vérification OTP (e-mail, 6 chiffres, Brevo).
- JWT access + refresh (HS256), mot de passe temporaire forcé au premier accès sensible,
  suspension/réactivation de compte (`Utilisateur.actif`), auto-suspension interdite.
- RBAC centralisé (`require_roles`, `verifier_portee_etablissement`) — audité une fois
  explicitement (3 trous RBAC trouvés et corrigés, voir §6).

### 3.2 Établissements & structure administrative
- Établissements (EP/ES/UP, public/privé), classes avec **année académique** et
  reconduction en lot, affectation enseignant↔classe précise (avec flag professeur
  principal), rentrée scolaire (ouverture/clôture, invitation tuteurs en masse).
- Annuaire public paginé + vitrine landing page + photos d'établissement (LuluFiles,
  carrousel), description éditable par l'A+/A++, suspension filtrée hors vitrine.
- Console établissement pivotée par classe/objet (élèves/enseignants/tuteurs/matières/notes).

### 3.3 Parcours élève
- Inscription (branche d'âge Art. 446 : consentement parental < 16 ans), validation par
  l'A+, génération de matricule national (formats UP à 8 car. / EP-ES à 9 car., compteur
  par cycle/nationalité/année, jamais réutilisé).
- Politique de dépassement de capacité par établissement (ordre d'arrivée / notes-concours /
  tirage au sort).

### 3.4 Recrutement enseignant
- Postes avec critères de notation par document (coefficient + seuil), formulaire de
  candidature dynamique (façon Google Forms, `ChampFormulaire[]`), notation IA en vision
  (FreeLLM) en arrière-plan, écran de révision manuelle si échec.
- Casier judiciaire chiffré (Fernet) stocké en base, jamais sur LuluFiles (Art. 395).
- Contestation, contrat (signature électronique par tracé canvas → PNG → LuluFiles, ADR-004),
  reconduction.

### 3.5 Pédagogie quotidienne
- Cours (texte/PDF/audio/**vidéo**), quiz généré par IA (QCM 4 choix), historique de
  tentatives.
- **Vie scolaire** (absences/retards/appréciations/incidents/félicitations), historique
  immuable, portée : professeur principal et admin voient tout, enseignant de matière ne
  voit que ses propres entrées.
- **El Professor** — assistant IA à 4 personas distinctes (élève, enseignant, tuteur,
  famille), avec garde-fou de sécurité par mots-clés (maltraitance, violence, danger...)
  déclenchant une alerte administrative à l'établissement (jamais visible du tuteur si
  l'alerte vient d'un fil familial où il pourrait être la source du danger).
- **Sessions en direct** — tableau collaboratif temps réel (WebSocket, traits/texte/
  effacement en append-only, panneaux, permissions de craie prêtée/accordée, file de
  demandes), chat de session, salle sociale pré-cours, signalisation WebRTC en maillage
  pour l'audio/vidéo (pas de SFU tiers), résumé asynchrone généré par IA à la clôture
  (texte du chat + blocs texte du tableau).

### 3.6 Évaluations & bulletins
- Devoirs formatifs/sommatifs (les formatifs exclus du bulletin), sujet et barème en
  document, soumission texte ou **copie photographiée** (correction holistique par IA
  vision), correction manuelle de secours.
- Référentiels de coefficients (gouvernance nationale, éditables par l'A++, proposition
  par l'A+ avec validation groupée), bulletin à moyenne pondérée.

### 3.7 Actes académiques
- Catalogue par établissement, demande (réclamation gratuite ou acte payant Kkiapay),
  traitement par l'A+. (Limite assumée : pas encore d'upload de pièces justificatives —
  documenté, non corrigé par choix de ne pas complexifier un endpoint déjà livré.)

### 3.8 Vie extra-scolaire
- **Transport/cantine** — tickets par élève, capacité par date, validation par un
  Contrôleur désigné + paiement confirmé, remboursement borné (veille 18h / avant
  validation, Art. 354).
- **Billetterie** — événements, billets gratuits/payants, annulation → remboursement
  intégral automatique (Art. 356), parrain délégué sans nouveau rôle.
- **Visites virtuelles 3D/drone** — publication A+/A++, lien externe (attestation
  d'autorisation déclarative, drone/ANAC et droit à l'image hors périmètre logiciel).
  Frontend volontairement laissé en teaser « Bientôt disponible ».
- **Ticketerie unifiée QR** — génération PDF avec QR code (transport/cantine/billetterie),
  scan natif navigateur (`BarcodeDetector`, aucune dépendance ajoutée).

### 3.9 Économie étudiante
- **Marketplace** (annonces, photos, signalement, séquestre, contestation) — réservée aux
  étudiants (établissement UP, validé), vendeur/acheteur du même établissement, arbitrage
  par l'A+.
- **Micro-jobs** (offres, missions, séquestre) — client ouvert aux adultes + étudiants,
  prestataire réservé aux **seuls étudiants** (revenu d'appoint, pas un service entre
  adultes) ; arbitrage/reversement par l'A++ (aucun établissement résoluble côté micro-job).
- Règle d'arbitrage utilisateur du 2026-09-26 resserrant les deux modules aux étudiants
  (élève inscrit et validé dans un établissement de type UP), documentée et testée.

### 3.10 Innovations familiales (volet Élève/Tuteur)
- **Coffre-fort familial** — opt-in strict (aucune restriction par défaut) : plafond
  hebdomadaire (alerte passive, jamais bloquante) et/ou seuil de validation (bloque
  l'amorçage du paiement jusqu'à décision du tuteur, jamais un blocage silencieux),
  couvre micro-jobs/marketplace/actes, relevé financier consolidé.
- **Radar familial** — digest hebdomadaire à la demande (jamais poussé), généré à partir
  de faits déjà établis ailleurs (vie scolaire, devoirs, sessions live, activité
  financière), transparence totale sur les sources citées.
- **Passeport de compétences** — agrège quiz réussis, cours suivis, moyennes par matière,
  badges dérivés d'agrégats réels (jamais un critère arbitraire), export PDF.
- **El Professor Famille** — fil partagé tuteur↔enfant, inutilisable tant que l'enfant n'a
  pas explicitement rejoint.

### 3.11 Gouvernance & supervision
- **Admin ministériel (refonte)** — `DataTable` générique réutilisable, établissements en
  datatable (suspendre/réactiver en lot), référentiels (édition inline + validation
  groupée), arbitrage micro-jobs en file d'attente avec tout le contexte, supervision
  transverse utilisateurs/cours/devoirs/événements (masquage non destructif), journal
  d'audit filtrable.
- **Admin établissement (refonte)** — rentrée scolaire, vie scolaire portable entre
  établissements, classes avec année académique, console pivot, recrutement/actes avec
  formulaire dynamique partagé, ticketerie QR, restriction étudiants sur micro-jobs/
  marketplace.

### 3.12 Transverse
- Messagerie (DM + groupe de classe calculé dynamiquement, jamais stocké — reste à jour
  sans hook cross-module), modération par signalement.
- Paiement Kkiapay centralisé (une seule URL de webhook pour tout le compte, essaie
  chaque type de ressource payante en séquence).
- Audit ministériel (`journaliser_action_ministerielle`, point d'entrée unique, jamais
  construit à la main dans un router).

## 4. État de validation par lot

| Lot | UC | Tests backend | Validation frontend |
|---|---|---|---|
| Phase 1 (socle) | UC-01 à UC-10 | 75 (e2e inclus) | Parcours réel en navigateur, 5 rôles, sans mocks |
| Phase 2/3 | UC-11 à UC-19 | 45 (120 cumulés) | Parcours réel en navigateur (8/9 UC, UC-19 en teaser) |
| Phase 4 (marketplace) | UC-20 à UC-22 | 11 (143 cumulés) | `tsc -b`+`vite build`, pas de parcours manuel (pas de Postgres local à l'époque) |
| Phase 5 (admin ministériel) | UC-23 à UC-38 (numérotation propre à ce lot) | 163 cumulés | Parcours réel (navigateur + curl) contre `seed_mega.py` |
| Phase 6 (admin établissement) | UC-39 à UC-58 (numérotation propre à ce lot) | 175 cumulés | `tsc -b`+`vite build`, pas de parcours manuel (demande explicite de vérifier le structurel) |
| Volet Professeur | UC-23 à UC-28 (numérotation propre à ce lot) | 213 cumulés | `tsc -b`+`vite build`+`oxlint`, pas de parcours manuel |
| Volet Élève/Tuteur | UC-29 à UC-38 (numérotation propre à ce lot) | 213 cumulés | **Playwright réel** (seul lot avec parcours automatisé en navigateur pour cette génération de fonctionnalités) |
| Fusion des deux lots parallèles | — | **239** (post-fusion, conflits résolus) | `tsc -b`+`vite build`+`oxlint` au vert |

⚠️ Les deux paires « Phase 5/6 admin ministériel-établissement » et « volet
Professeur/Élève-Tuteur » ont été développées en parallèle sur deux branches distinctes et
partagent donc la même numérotation UC-23 à UC-38/58 sous des noms différents — collision
de numérotation documentaire, pas de recouvrement fonctionnel réel (vérifié à la fusion).
À renuméroter proprement si un cahier des charges consolidé est un jour requis.

## 5. Limites connues / dette technique assumée

- Micro-jobs : reversement prestataire manuel (Kkiapay n'offre pas de transfert ponctuel
  par mission, ADR-008).
- Actes académiques : pas d'upload de pièces justificatives malgré le cas d'utilisation
  d'origine (bascule JSON→multipart jugée trop risquée pour un gain jugé secondaire).
- Visites virtuelles 3D/drone : frontend en teaser, choix technique de la visite 3D
  elle-même non arbitré.
- Cours en direct : pas d'enregistrement serveur rejouable (signalisation WebRTC en
  maillage sans SFU — limite structurelle assumée), seul le tableau (traits + capture PNG)
  est rejouable.
- Coffre-fort : aucune UI n'existait pour configurer les plafonds au moment de la clôture
  du backend (à vérifier après fusion — le frontend `CoffreFortPage.tsx` existe côté
  volet Élève/Tuteur, cf. §3.10).
- **`scripts/seed_mega.py` n'est pas à jour** avec les deux derniers lots (vie scolaire,
  tableau collaboratif, El Professor enseignant/tuteur/famille, Coffre-fort, rentrée
  scolaire, photos d'établissement, formulaire dynamique, ticketerie QR, masquage
  cours/devoirs, restriction étudiants) — chantier en cours, voir le commit dédié.
- Désignation de contrôleur/parrain : partiellement résolue (transport/cantine via
  recherche par nom) ; contrôleur par événement et parrain restent en saisie d'ID brut.
- Pas de tests automatisés frontend (unitaires ou end-to-end) en dehors des parcours
  manuels/Playwright ponctuels documentés ci-dessus.
- Une CVE transitive non bloquante (`ecdsa` 0.19.2` via `python-jose`, pas de fix
  disponible, chemin vulnérable jamais emprunté — HS256 utilisé partout).

## 6. Conformité légale (loi n° 2017-20, points déjà couverts)

- Art. 446 (protection des mineurs) — branche d'âge à l'inscription, consentement
  parental horodaté et démontrable (Art. 389-390), micro-jobs/marketplace réservés aux
  majeurs numériques/étudiants.
- Art. 395 (données sensibles) — casier judiciaire chiffré et gardé en base, jamais
  confié à un tiers de stockage de fichiers.
- Art. 284-287 (signature électronique) — signature simple par tracé canvas, choix
  assumé (pas de signature qualifiée) pour les contrats enseignants.
- Art. 401 (décisions automatisées sans recours) — toute notation/correction IA dispose
  d'un écran de révision manuelle humaine en cas d'échec ou de contestation.
- Art. 354/356 (remboursements) — bornes précises sur transport/cantine et billetterie.

## 7. Stack technique (résumé)

Backend FastAPI (Python 3.13) + SQLAlchemy 2.0/Alembic + PostgreSQL · Frontend React 19 +
Vite + TypeScript + Tailwind v4 · Paiement Kkiapay · IA FreeLLM (API compatible OpenAI) ·
Stockage fichiers LuluFiles · Déploiement Render (backend+DB) / Vercel-Netlify (frontend) ·
CI GitHub Actions. Détail et justification : [docs/choix-technique-phase1.md](choix-technique-phase1.md)
et [docs/adr/](adr/).
