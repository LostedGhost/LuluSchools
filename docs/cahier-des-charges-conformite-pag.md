# Cahier des charges — Lot 7 : conformité PAG 2021-2026 et inclusion (Challenge EduTech Bénin)

Statut : **proposé, en attente de validation** (étape 1 du pipeline `lucio-dev`).
Date : 2026-09-28.

## 1. Pourquoi ce lot

LuluSchools répond au Challenge EduTech Bénin, qui impose un « minimum non négociable » :
plateforme **fonctionnelle et inclusive** (handicap visuel ou auditif, quel que soit le niveau
d'alphabétisation), **pensée pour une connectivité limitée**, avec gestion de contenu, dépôt
GitHub et déploiement en ligne. Le jury note : profondeur de la réflexion sur les usages,
design, fonctionnement, qualité du code.

La solution doit aussi s'aligner sur le **PAG 2021-2026**, Pilier 2, axe 5 « Promotion d'une
éducation de qualité et de l'EFTP » (8,3 % du portefeuille), qui compte 4 actions :

1. poursuivre la restructuration du système éducatif (qualité des formations, conditions d'études) ;
2. développer l'enseignement et la formation techniques et professionnels (EFTP) ;
3. promouvoir la recherche et l'innovation (dont les bourses pour les filières scientifiques) ;
4. **promouvoir l'alphabétisation et l'éducation des adultes**.

S'y ajoutent des volets transverses : SMART GOUV et dématérialisation, compétences numériques
dans le système éducatif, bonne gouvernance, redevabilité, suivi-évaluation, insertion des jeunes
et inclusion financière.

## 2. Constat vérifié dans le code (2026-09-28)

| Exigence | État | Preuve |
|---|---|---|
| GitHub, déploiement, gestion de contenu | OK | CI verte, `lulu-schools.vercel.app` et le backend Render répondent en 200 |
| Lecteur d'écran | **KO** | `frontend/index.html` : `lang="en"` ; aucun lien d'évitement ; `sr-only` présent une seule fois |
| Lecture à voix haute | Partiel | Seulement dans El Professor (`LlmClient.synthese_vocale`, dictée Web Speech) |
| Handicap auditif | **KO** | `Cours` (audio/vidéo) sans transcription ni sous-titres ; aucune balise `<track>` |
| Non-alphabétisés | **KO** | Aucune navigation par pictogrammes ou par la voix, aucune langue nationale |
| Connectivité limitée | Partiel | Pas de service worker ; bundle principal 945 Ko (une seule route en `lazy`) ; Three.js chargé même en mode économie de données. Point fort : la **saisie papier** |
| Suivi-évaluation ministériel | **KO** | Tableau A++ sans indicateur éducatif ; tuile « Couverture académique » **codée en dur à 3** ; `Etablissement` sans département/commune, élève sans sexe → aucune statistique territoriale ni de parité possible |
| Alphabétisation (PAG action 4) | Absent | — |
| EFTP, bourses (PAG actions 2-3) | Faible | Pas de parcours spécifique ; le passeport de compétences s'en approche |

## 3. Principe directeur : ne rien retirer, tout repositionner

Aucune innovation déjà livrée n'est supprimée. Chacune est **rattachée explicitement à une
orientation du PAG** (dans l'interface et dans le dossier du jury) et, si besoin, allégée pour
les connexions lentes.

| Innovation existante | Rattachement PAG / challenge | Ajustement prévu |
|---|---|---|
| Saisie papier (notes, appel, copies, contrats) | Connectivité limitée, inclusion des acteurs sans smartphone | Mise en avant n°1 dans le dossier du jury |
| El Professor (chat, voix, dictée) | Qualité des enseignements ; accessibilité | Sa synthèse vocale est réutilisée par la barre d'accessibilité (Lot 7.2) |
| Recrutement par IA avec recours humain | Restructuration du système éducatif, bonne gouvernance | — |
| Référentiels de coefficients validés par le ministère, journal d'audit | Gouvernance, redevabilité | Alimentent le tableau de pilotage (Lot 7.6) |
| Cantine et transport | Conditions d'études ; loi sur le financement des cantines scolaires | Nombre de bénéficiaires affiché dans les indicateurs |
| Passeport de compétences | Réforme des compétences numériques ; EFTP | Enrichi de compétences métier (Lot 7.8) |
| Micro-jobs, marketplace étudiante | Insertion des jeunes (« Projet d'inclusion des jeunes », programme de stages) | Offres de stage (Lot 7.8) |
| Paiement Kkiapay / mobile money | Inclusion financière (Pilier 3) | — |
| Cours en direct, tableau collaboratif | Numérique dans l'enseignement supérieur | Le résumé texte existant sert aussi aux sourds et malentendants |
| Coffre-fort familial, radar familial | Implication des familles | Radar lisible à voix haute (Lot 7.4) |
| Billetterie, visites 3D, scène 3D | Attractivité, vitrine | Conservées ; Three.js désactivé en mode « données réduites » (Lot 7.5) |

## 4. Lots proposés

Priorité : **P0** = exigé par le challenge (éliminatoire), **P1** = alignement PAG,
**P2** = différenciant. Numérotation des cas d'utilisation à partir d'UC-71.

### Lot 7.1 — Socle d'accessibilité (P0, ~0,5 j)

- UC-71 : `lang="fr"`, repères sémantiques (`header`/`nav`/`main`), lien « Aller au contenu »,
  `:focus-visible` global, nom accessible sur tous les boutons-icônes `lucide-react`, `alt` sur
  toutes les images, annonces `aria-live` sur les notifications.
- Contrôle : étendre `frontend/scripts/audit_ergonomie.js` avec axe-core → **0 violation
  critique ou sérieuse** sur les 15 pages clés des 5 rôles.

### Lot 7.2 — Barre d'accessibilité globale (P0, ~1 j)

- UC-72 : « Écouter cette page » : `speechSynthesis` (voix fr-FR) en priorité, repli sur
  `synthese_vocale` de FreeLLM si le navigateur n'a pas de voix française.
- UC-73 : taille du texte (3 niveaux), contraste élevé, espacement renforcé, réduction des
  animations. Préférences dans `localStorage` et synchronisées sur le profil (`PATCH /me`) pour
  suivre l'utilisateur d'un appareil à l'autre.
- Critère : parcours « consulter le bulletin » faisable au clavier seul et avec NVDA.

### Lot 7.3 — Handicap auditif (P0, ~1 j)

- UC-74 : champ `transcription` sur `Cours`, **obligatoire** pour publier un cours audio ou vidéo
  (migration dédiée) ; affichage synchronisé sous le lecteur ; sous-titres WebVTT facultatifs
  (`<track>`).
- UC-75 : l'IA met en forme la transcription fournie par l'enseignant (paragraphes, titres) et en
  tire un résumé. **À vérifier avant de coder** dans le dépôt `freellm-lucio` : si un endpoint
  `/v1/audio/transcriptions` existe (Whisper via un fournisseur gratuit), la transcription peut
  être générée automatiquement puis relue par l'enseignant (Art. 401 : validation humaine).
- Toute alerte sonore a un équivalent visuel (déjà le cas, à vérifier).

### Lot 7.4 — Mode « Écoute » pour les personnes non alphabétisées (P0/P1, ~2 j)

- UC-76 : accueil simplifié du tuteur, activable à l'inscription ou au guichet (saisie papier) :
  6 grandes tuiles pictogrammes (Bulletin, Présences, Paiements, Messages, Cantine, Aide), chaque
  tuile **se lit à voix haute** au toucher.
- UC-77 : bulletin et radar familial convertis en phrases orales simples (« Votre enfant a 12 de
  moyenne au 1er trimestre, il est admis »), générées côté serveur sans IA (déterministes, donc
  fiables).
- UC-78 : messages vocaux dans la messagerie (MediaRecorder → LuluFiles, durée plafonnée), pour
  échanger avec l'enseignant sans écrire.
- Langues : libellés fixes du mode Écoute (~30 phrases) enregistrés en **fon et yoruba** (fichiers
  audio statiques, légers, mis en cache) ; contenus dynamiques en français par synthèse vocale.
  `[Délégué]` Choix de fon + yoruba : ce sont les deux langues nationales les plus parlées dans
  le Sud, où se trouvent les établissements de démonstration ; d'autres langues (bariba, dendi…)
  s'ajoutent en déposant des fichiers, sans code.

### Lot 7.5 — Connectivité limitée (P0, ~1,5 j)

- UC-79 : PWA (`vite-plugin-pwa`) : application installable, cache des pages et des cours déjà
  consultés, bandeau « hors ligne ».
- UC-80 : file d'attente hors ligne pour les soumissions de devoir et l'appel, envoyée au retour du
  réseau (idempotence côté serveur par clé client).
- UC-81 : mode « données réduites », automatique si `navigator.connection.saveData` ou réseau
  2G/3G lent : pas de Three.js ni d'objets 3D, images réduites, pas de lecture automatique des
  médias.
- Découpage du bundle : toutes les routes par rôle en `lazy()`. Budget : **< 250 Ko gzip au
  premier chargement**, mesuré en CI.
- La saisie papier reste la réponse pour les zones sans réseau ; elle est présentée comme telle.

### Lot 7.6 — Pilotage ministériel et suivi-évaluation (P1, ~1,5 j)

- UC-82 : `Etablissement.departement` et `commune` (12 départements, 77 communes du Bénin, liste
  fermée) et `Eleve.sexe` (migration + seed mis à jour).
  `[Délégué]` Le sexe est une donnée personnelle ordinaire (pas sensible au sens de l'Art. 394) ;
  elle est collectée pour une finalité statistique déclarée et n'est exposée qu'agrégée au
  ministère, avec un seuil minimal d'effectif (pas de case < 5 élèves) contre la réidentification.
- UC-83 : `GET /admin/indicateurs` : effectifs par département/type/statut et par sexe, taux de
  réussite (moyenne ≥ 10) et indice de parité filles/garçons, taux de présence (vie scolaire),
  ratio élèves/enseignant, bénéficiaires de cantine, enseignants recrutés sur l'année. Filtres :
  année académique, département. Export CSV.
- UC-84 : tableau A++ refondu avec ces indicateurs réels (suppression de la tuile codée en dur) et
  un encart « Alignement PAG » qui relie chaque indicateur à son orientation.

### Lot 7.7 — Alphabétisation et éducation des adultes (P1, ~1,5 j)

- UC-85 : nouveau type d'établissement « centre d'alphabétisation » et classes pour adultes, sans
  consentement parental ni matricule scolaire classique (un matricule adulte dédié).
- UC-86 : cours « audio d'abord » (audio + pictogrammes + texte court) et quiz oral : question lue,
  réponses sous forme d'images. Réutilise pédagogie, quiz et le mode Écoute (7.4).
- UC-87 : un tuteur en mode Écoute peut s'inscrire lui-même à un cours d'alphabétisation : la
  boucle « le parent apprend avec la plateforme de son enfant » devient un argument pour le jury.

### Lot 7.8 — EFTP, sciences et insertion (P2, ~1 j)

- UC-88 : filières techniques et professionnelles sur les classes (type d'enseignement) ; le
  passeport de compétences accepte des compétences métier validées par l'enseignant.
- UC-89 : offres de stage publiées par des entreprises partenaires (réutilise micro-jobs, sans
  séquestre), ce qui couvre les « structures gravitant autour de l'éducation » de l'énoncé.
- UC-90 : demande de bourse pour les filières scientifiques, sous forme d'acte académique
  dynamique (`FormulaireBuilder`) avec pré-contrôle d'éligibilité sur les moyennes en sciences.

### Lot 7.9 — Dossier du jury (P0, ~0,5 j)

- Page publique `/a-propos/pag` et section du README : tableau « orientation PAG → fonctionnalité
  → écran à tester ».
- Comptes de démonstration dédiés : « tuteur non alphabétisé (mode Écoute, fon) », « élève
  malvoyant », « centre d'alphabétisation », avec un script de démo de 5 minutes.

## 5. Ordre de réalisation

| Étape | Lots | Résultat |
|---|---|---|
| 1 | 7.1, 7.2, 7.5 (hors file hors ligne), 7.9 | Minimum non négociable du challenge couvert |
| 2 | 7.3, 7.4, 7.6 | Handicap auditif, non-alphabétisés, suivi-évaluation PAG |
| 3 | 7.7, 7.8, file hors ligne (UC-80) | Actions PAG 2 à 4 couvertes |
| 4 | Validation de bout en bout, audit axe-core, Lighthouse en 3G simulée, redéploiement | Preuves chiffrées pour le jury |

Charge totale estimée : ~10,5 jours-développeur, dont ~3,5 jours pour l'étape 1.

## 6. Critères d'acceptation globaux

- axe-core : 0 violation critique ou sérieuse sur les 15 pages clés.
- Lighthouse mobile en 3G lente : accessibilité ≥ 95, performance ≥ 70 sur la landing page et le
  tableau de bord élève.
- Un cours déjà consulté reste lisible en mode avion.
- Parcours « tuteur non alphabétisé » réalisable sans lire un seul mot.
- Tableau A++ : aucun chiffre codé en dur ; chaque indicateur est recalculable depuis la base.
- Aucune régression : suite pytest verte sous SQLite et PostgreSQL, `tsc -b`, `vite build`, `oxlint`.

## 7. Points à valider par l'utilisateur

1. Priorités et périmètre des lots 7.7 et 7.8 : à faire maintenant ou après le rendu du challenge ?
2. Enregistrements audio en fon et yoruba : qui les réalise (voix humaine locale, recommandé)
   ou synthèse provisoire en attendant ?
