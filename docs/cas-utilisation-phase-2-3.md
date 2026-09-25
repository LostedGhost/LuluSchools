# LuluSchools — Cas d'utilisation, Phases 2 et 3

Rédigé selon la méthode `lucio-dev` (pipeline spec-first), même format que `docs/cas-utilisation-phase-1.md`. Chaque cas d'utilisation liste ses règles métier précises ; les points encore ouverts sont marqués 🔓. **Ce document doit être explicitement validé comme complet avant de passer à l'étape 2 (diagrammes UML) pour ces deux phases** — aucun code ni modèle de données ne doit être produit avant cette validation (voir skill `lucio-dev`).

Cadrage : mandat ministériel officiel, premier déploiement au Bénin, conformité suivie sur la loi n° 2017-20 (skill `droit-numerique-benin`). Paiement/séquestre via Kkiapay, même modèle de compte unique que pour les actes académiques (UC-10) : LuluSchools n'héberge jamais les fonds elle-même.

Phasage de référence (voir `SUIVI-PROJET.md`) :
- **Phase 2** : tickets transport/cantine, messagerie interne, assistant IA "El Professor" (les items "réclamations" et "actes payants" initialement prévus en Phase 2 ont déjà été absorbés dans la Phase 1 — UC-04b et UC-10).
- **Phase 3** : vidéo/podcast/live, billetterie d'événements, micro-jobs + séquestre, visites 3D/drone.

## Acteurs (rappel RBAC, inchangé depuis la Phase 1)

A++ (admin ministériel) · A+ (admin établissement) · A- (admin/décideur passif, lecture seule) · P (enseignant) · Élève/Étudiant · Tuteur · **Contrôleur/Ticketeur** (rôle temporaire, désigné par l'A+, valide les tickets/billets à l'entrée) · **Prestataire micro-job / Parrain d'événement** (déjà anticipés dans le RBAC de la Phase 1, non encore implémentés).

---

# Phase 2

## UC-11 — Achat d'un ticket de transport scolaire

> En tant qu'élève ou tuteur, je veux acheter un ticket de transport scolaire pour un trajet donné, afin d'utiliser la navette de mon établissement.

- Catalogue de lignes/trajets défini par établissement (A+) : nom de ligne, prix, capacité par trajet (nombre de places).
- Achat : élève ou tuteur choisit une ligne + une date de trajet ; paiement Kkiapay avant confirmation (même mécanique que UC-10 : `POST .../paiement/amorcer` puis webhook).
- Statuts : `acheté` → `validé` (scanné/tamponné à l'embarquement par le Contrôleur/Ticketeur désigné sur cette ligne) → `expiré` (date de trajet dépassée sans validation) → `remboursé`.
- **Remboursement (Art. 354 — perte du droit de rétractation pour un service intégralement fourni)** : un ticket déjà `validé` (embarquement effectué) n'est jamais remboursable. Un ticket non utilisé peut être remboursé jusqu'à une heure limite avant le trajet.
  - 🔓 Heure limite exacte de remboursement (proposition par défaut : jusqu'à la veille 18h).
  - 🔓 Vente à l'unité seulement, ou abonnement multi-trajets (semaine/mois) ? Proposition : ticket à l'unité en V1, abonnement en évolution ultérieure.
- Capacité de la ligne atteinte → achat refusé (`409`), pas de liste d'attente en V1 🔓 (à confirmer).

## UC-12 — Achat d'un ticket cantine

> En tant qu'élève ou tuteur, je veux acheter un ticket de repas pour une date donnée, afin d'accéder au service de cantine de mon établissement.

- Catalogue défini par établissement (A+) : prix du repas (peut varier par jour/menu), capacité de service par jour.
- Même cycle de vie qu'UC-11 (`acheté` → `validé` au service → `expiré` → `remboursé`), même heure limite de remboursement (Art. 354, service fourni en une fois dès le repas servi).
- 🔓 Information allergènes/régime alimentaire particulier : hors périmètre V1 (pas de champ dédié), à confirmer si nécessaire avant implémentation.
- 🔓 Un même rôle Contrôleur/Ticketeur peut-il valider transport ET cantine, ou faut-il une désignation séparée par service ? Proposition : une désignation par service (un contrôleur peut cumuler les deux, mais l'A+ les attribue séparément).

## UC-13 — Messagerie interne

> En tant qu'utilisateur authentifié (tuteur, élève, enseignant, A+, A++), je veux échanger des messages texte avec un autre utilisateur ou avec le groupe de ma classe, afin de communiquer dans le cadre scolaire.

- Deux types de conversation : **1-à-1** (entre deux utilisateurs) et **groupe de classe** (auto-créé à la création de la classe, membres = enseignant(s) rattaché(s) + élèves inscrits + tuteurs rattachés à ces élèves ; mise à jour automatique à chaque inscription/désinscription).
- Format V1 : texte uniquement, pas de pièce jointe ni d'image 🔓 (à confirmer — simplifie fortement la modération).
- **Règle verrouillée pour raison légale (Art. 519 — sollicitation de mineurs ; Art. 521 — corruption de mineur, peines aggravées explicitement "dans les établissements d'enseignement" ; Art. 550 — harcèlement par communication électronique)** : toute conversation impliquant au moins un élève mineur (<18 ans, ou reprendre le seuil déjà utilisé <16 ans pour le consentement 🔓 à trancher) est journalisée de façon inaltérable côté serveur (une suppression par un participant ne fait que la masquer de son propre écran, jamais du stockage serveur) et consultable par l'A+ de l'établissement de l'élève sur signalement. Chaque message affiche un bouton "signaler" visible par tous les participants ; un signalement notifie immédiatement l'A+ concerné.
- 🔓 **Décision produit encore ouverte** (pas légalement tranchée, à valider par toi) : autorise-t-on les messages 1-à-1 libres entre un adulte (enseignant/admin) et un élève mineur, ou restreint-on ces échanges au groupe de classe supervisé uniquement (DM adulte↔mineur interdit, DM adulte↔tuteur et élève↔élève/groupe classe autorisés) ? Recommandation : la deuxième option réduit fortement le risque et la surface de modération nécessaire, mais c'est ton produit — à trancher explicitement avant l'étape UML.
- 🔓 Durée de conservation des messages avant purge (proposition : pas de purge automatique en V1, alignée avec la conservation à des fins de preuve/signalement).
- 🔓 Canal de notification à réception d'un message (email via Brevo déjà en place, ou notification in-app seule en V1 ?).

## UC-14 — Assistant IA pédagogique "El Professor"

> En tant qu'élève, je veux poser des questions à un assistant IA conversationnel sur le contenu d'un cours, afin d'obtenir des explications complémentaires à mon rythme, en dehors de la présence de l'enseignant.

- Basé exclusivement sur FreeLLM (jamais l'API Anthropic en direct — ADR-002).
- Contexte fourni au modèle : le `contenu_texte` du cours concerné (même source que la génération de quiz, UC-07).
- L'assistant ne donne jamais directement la réponse d'un devoir non encore soumis par l'élève (garde-fou de prompt) — cohérent avec l'esprit d'UC-08 (l'évaluation reste un exercice réel de l'élève).
- Aucune note, décision ou statut n'est produit par cet assistant (pas de décision automatisée à effet significatif — cohérent avec Art. 401, déjà appliqué ailleurs sur la plateforme).
- 🔓 **Portée encore ouverte** : uniquement un tuteur pédagogique pour l'élève sur le contenu d'un cours donné, ou aussi un guide d'usage de la plateforme pour les autres rôles (tuteur, enseignant, A+) comme évoqué à l'origine de l'idée ? Ce point change fortement le périmètre technique — à trancher avant UML.
- 🔓 Historique de conversation conservé par élève et par cours, ou session éphémère non stockée ? Impacte le modèle de données.

---

# Phase 3

## UC-15 — Contenu vidéo/podcast pédagogique (asynchrone)

> En tant qu'enseignant, je veux publier un contenu vidéo ou podcast pour ma classe, afin d'enrichir mes cours au-delà des formats texte/PDF/audio déjà disponibles (UC-06).

- Extension directe d'UC-06 : mêmes règles de rattachement (classe/matière/chapitre, visible uniquement par les élèves inscrits pour l'année en cours), nouveau format `video` (mp4) en plus de `markdown`/`pdf`/`audio`.
- Stockage via LuluFiles (cohérent ADR-003), sauf si le format/poids vidéo dépasse ce que permet le plan LuluFiles actuel.
- 🔓 **Point bloquant hérité de la Phase 1** : le plan gratuit LuluFiles ("Lancement") est plafonné à 5 Go de transfert/mois et 2 Mo/s partagés (voir `docs/adr/ADR-003-stockage-fichiers-lulufiles.md`) — la vidéo consomme largement plus de bande passante que texte/PDF/audio. Ce point doit être retranché avec toi avant l'implémentation (passage à un plan payant, ou limite de taille/durée stricte par vidéo).
- 🔓 Taille/durée max par vidéo (proposition par défaut : 200 Mo / 15 minutes, à confirmer).

## UC-16 — Cours en direct (live)

> En tant qu'enseignant, je veux animer une session de cours en direct avec ma classe, afin de dispenser un enseignement interactif à distance en complément des contenus publiés.

- **Consentement renforcé (extension légale d'Art. 446, décision que je verrouille sur le fondement du même article que le consentement d'inscription)** : un élève mineur ne peut activer sa caméra/son micro en session live qu'après un consentement explicite et horodaté d'un tuteur couvrant spécifiquement "la participation avec image/voix à des sessions en direct" — distinct du consentement d'inscription générique (UC-01/UC-02), car il couvre un traitement d'image différent. Un élève sans ce consentement peut suivre la session en lecture seule (audio du professeur + chat texte), jamais bloqué hors de la classe.
- **Enregistrement de la session** : proposition par défaut (à confirmer) — **pas d'enregistrement automatique en V1**. Un enregistrement expose les élèves filmés à un traitement d'image supplémentaire (Art. 576 — atteinte à la représentation de la personne, en cas de diffusion sans autorisation) qui nécessiterait un consentement encore distinct de tous les tuteurs présents ce jour-là ; reporté hors V1 pour ne pas bloquer la fonctionnalité principale.
- 🔓 Infrastructure technique de diffusion (WebRTC/SFU, fournisseur) — décision technique, pas une règle métier, tranchée à l'étape 3 (choix technique) une fois cette UC validée.
- 🔓 Nombre max de participants simultanés par session (dépend du choix technique ci-dessus).

## UC-17 — Billetterie d'événements scolaires

> En tant qu'A+ (ou "Parrain d'événement" désigné par lui), je veux créer un événement avec billetterie payante ou gratuite, afin d'organiser une manifestation ouverte aux familles (kermesse, remise de diplômes, spectacle).

- Champs : titre, description, lieu, date/heure, capacité max, prix par billet (0 si gratuit).
- Achat par tout utilisateur authentifié de la plateforme (élève, tuteur, enseignant, admin) 🔓 — un public externe sans compte est-il autorisé à acheter un billet, ou faut-il obligatoirement un compte LuluSchools ? Proposition : compte requis, cohérent avec le reste de la plateforme (pas d'achat anonyme).
- Paiement Kkiapay, même mécanique que UC-10/UC-11/UC-12.
- Billet = référence unique scannée à l'entrée par un Contrôleur/Ticketeur désigné pour l'événement (rôle temporaire, comme UC-11/UC-12).
- **Remboursement (Art. 354, cohérent avec UC-11/UC-12)** : billet scanné à l'entrée → jamais remboursable. Avant l'événement, remboursable jusqu'à une heure limite 🔓 (proposition : jusqu'à 48h avant, plus long qu'un ticket de transport/cantine car achat souvent anticipé).
- **Annulation de l'événement par l'organisateur (Art. 356 — résolution pour manquement contractuel)** : remboursement intégral obligatoire de tous les billets vendus, déclenché automatiquement à l'annulation.
- 🔓 Catégories de billets (adulte/enfant/famille) ou tarif unique par événement en V1 ? Proposition : tarif unique en V1.

## UC-18 — Micro-jobs entre pairs avec séquestre

> En tant qu'utilisateur de la plateforme, je veux proposer ou accepter une mission rémunérée de courte durée (tutorat, petite mission de service), afin d'échanger un service contre rémunération de façon sécurisée par séquestre.

- 🔓 **Point bloquant à traiter avant toute spécification plus poussée de cette UC, hors périmètre de la loi n° 2017-20** : l'âge minimum légal pour qu'un élève **mineur** perçoive une rémunération pour un travail relève du Code du travail béninois, pas du droit numérique — je ne peux pas trancher ce point avec le skill `droit-numerique-benin`. Il faut une confirmation ministérielle/juridique séparée avant d'autoriser un élève mineur à être **prestataire** (à l'inverse, être seulement **client** d'un micro-job proposé par un majeur pose moins de risque et pourrait être ouvert plus tôt).
- Rôle "Prestataire micro-job" : déjà anticipé dans le RBAC de la Phase 1, pas encore de règle d'attribution définie — 🔓 qui peut devenir prestataire (tout enseignant/tuteur majeur ? validation préalable par l'A+ ?).
- **Séquestre** : le paiement Kkiapay du client est retenu jusqu'à validation de la mission ; le prestataire n'est payé qu'après cette validation. LuluSchools n'héberge jamais les fonds elle-même (cohérent ADR-003) — 🔓 à vérifier concrètement si l'API Kkiapay porte elle-même un mécanisme de séquestre (fonds bloqués chez eux jusqu'à libération), ou si LuluSchools doit modéliser un délai de rétention avant reversement de son côté — ce point technique dépend de la documentation réelle de Kkiapay, à consulter à l'étape 3.
- 🔓 Mécanisme de litige (le client conteste la qualité de la mission après paiement retenu) — aucune règle définie aujourd'hui, à spécifier entièrement.
- 🔓 Commission éventuelle de la plateforme sur chaque mission (%) — à confirmer.

## UC-19 — Visite virtuelle 3D / vidéo aérienne (drone) d'un établissement

> En tant qu'A+ (ou A++), je veux publier une visite virtuelle 3D ou une vidéo aérienne de mon établissement, afin de le présenter à distance aux familles et futurs candidats.

- 🔓 **Point purement administratif, hors périmètre de la loi n° 2017-20** : l'usage d'un drone relève de la réglementation aérienne béninoise (autorisation ANAC ou équivalent) — à obtenir par l'établissement/A+ avant tout tournage, ce n'est pas une règle que le logiciel peut faire respecter.
- **Droit à l'image des personnes filmées (Art. 576 — atteinte à la représentation de la personne, en cas de diffusion sans autorisation)** : toute prise de vue où des élèves ou membres du personnel sont identifiables nécessite leur consentement (ou celui de leur tuteur pour un mineur) avant publication.
  - 🔓 Modalité technique à trancher : floutage automatique des visages avant publication, tournage hors présence d'élèves, ou recueil de consentement individuel — les trois ont des implications très différentes sur le backend (aucune si tournage hors présence, traitement d'image si floutage automatique).
- 🔓 Format de diffusion : lien externe vers un service tiers (type Matterport) simplement référencé, ou upload natif via LuluFiles ? Le premier est beaucoup plus simple à implémenter (pas de traitement 3D côté LuluSchools).

---

## Points ouverts avant validation finale des Phases 2 et 3

**Légalement tranchés (décidés par moi, article cité — voir [[feedback-legal-autonomy]]) :**
1. Messagerie impliquant un mineur : journalisation inaltérable + signalement obligatoire (Art. 519, 521, 550).
2. Tickets/billets déjà consommés ou scannés : jamais remboursables (Art. 354).
3. Annulation d'un événement par l'organisateur : remboursement intégral obligatoire (Art. 356).
4. Participation caméra/micro d'un mineur en session live : consentement tuteur distinct et explicite requis (extension d'Art. 446).

**Purement administratifs, hors portée du logiciel (à traiter par toi/le ministère, pas par une décision technique) :**
5. Micro-jobs (UC-18) : âge minimum légal pour qu'un élève mineur soit rémunéré — Code du travail béninois, hors loi n° 2017-20.
6. Visites 3D/drone (UC-19) : autorisation de vol de drone — réglementation aérienne (ANAC), hors loi n° 2017-20.

**Décisions produit encore à ton arbitrage (aucune n'est légalement contrainte) :**
7. Messagerie (UC-13) : DM libres adulte↔mineur autorisés, ou restreints au groupe de classe supervisé ?
8. El Professor (UC-14) : uniquement un tuteur pédagogique sur le contenu de cours, ou aussi un guide d'usage plateforme pour tous les rôles ?
9. Vidéo pédagogique (UC-15) : le plan LuluFiles gratuit actuel tient-il la charge vidéo, ou faut-il déjà prévoir un plan payant avant la Phase 3 ?
10. Cours en direct (UC-16) : confirmer l'absence d'enregistrement automatique en V1.
11. Micro-jobs (UC-18) : Kkiapay porte-t-il lui-même le séquestre, ou LuluSchools doit-il le modéliser (délai de rétention) ?
12. Visites 3D/drone (UC-19) : floutage automatique, tournage sans élèves, ou consentement individuel ?
13. Divers réglages par défaut proposés ci-dessus (délais de remboursement, tailles/durées max, catégories de billets, etc.) — chacun marqué 🔓 dans son UC, à valider en bloc ou à ajuster.
