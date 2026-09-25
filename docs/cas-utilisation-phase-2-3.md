# LuluSchools — Cas d'utilisation, Phases 2 et 3

Rédigé selon la méthode `lucio-dev` (pipeline spec-first), même format que `docs/cas-utilisation-phase-1.md`. **Validé le 2026-09-25** : l'utilisateur a tranché explicitement le point UC-13 (DM adulte↔mineur) et a délégué l'arbitrage de tous les autres points ouverts restants. Toutes les décisions issues de cette délégation sont marquées **[Délégué]** ci-dessous pour rester traçables ; les deux points purement administratifs (hors portée du logiciel) restent signalés 🔓 car ils nécessitent une action humaine réelle (pas une décision produit) avant que la fonctionnalité correspondante soit réellement utilisable en production.

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
- **Remboursement (Art. 354 — perte du droit de rétractation pour un service intégralement fourni)** : un ticket déjà `validé` (embarquement effectué) n'est jamais remboursable. Un ticket non utilisé peut être remboursé jusqu'à la veille du trajet 18h **[Délégué]**.
- Vente à l'unité uniquement en V1, pas d'abonnement multi-trajets **[Délégué]** — un abonnement est une évolution ultérieure indépendante (pas de règle de dégressif de prix à inventer maintenant).
- Capacité de la ligne atteinte → achat refusé (`409`), pas de liste d'attente en V1 **[Délégué]**.

## UC-12 — Achat d'un ticket cantine

> En tant qu'élève ou tuteur, je veux acheter un ticket de repas pour une date donnée, afin d'accéder au service de cantine de mon établissement.

- Catalogue défini par établissement (A+) : prix du repas (peut varier par jour/menu), capacité de service par jour.
- Même cycle de vie qu'UC-11 (`acheté` → `validé` au service → `expiré` → `remboursé`), même heure limite de remboursement (Art. 354, service fourni en une fois dès le repas servi).
- Pas de champ allergènes/régime alimentaire en V1 **[Délégué]** — un régime alimentaire est une donnée de santé (Art. 394 — donnée sensible), son ajout mériterait sa propre UC avec un régime de consentement dédié plutôt qu'un champ texte libre improvisé ; hors périmètre tant que ce n'est pas explicitement demandé.
- Le rôle Contrôleur/Ticketeur est désigné par service (transport, cantine, ou un événement de la Phase 3) **[Délégué]** — une même personne peut cumuler plusieurs désignations, mais chaque désignation est une attribution explicite et distincte faite par l'A+, jamais un rôle global implicite.

## UC-13 — Messagerie interne

> En tant qu'utilisateur authentifié (tuteur, élève, enseignant, A+, A++), je veux échanger des messages texte avec un autre utilisateur ou avec le groupe de ma classe, afin de communiquer dans le cadre scolaire.

- Deux types de conversation : **1-à-1** et **groupe de classe** (auto-créé à la création de la classe, membres = enseignant(s) rattaché(s) + élèves inscrits + tuteurs rattachés à ces élèves ; mise à jour automatique à chaque inscription/désinscription).
- **Restriction DM adulte↔élève (décision explicite de l'utilisateur, 2026-09-25)** : un adulte (enseignant, A+, A++) ne peut échanger avec un élève **que via le groupe de classe**, jamais en conversation 1-à-1. Les conversations 1-à-1 restent ouvertes entre : tuteur↔enseignant, tuteur↔A+, tuteur↔tuteur, tuteur↔élève (son propre enfant rattaché), et élève↔élève. Un enseignant/A+ qui tente d'ouvrir un DM vers un compte Élève reçoit un refus (`403`) l'orientant vers le groupe de classe concerné.
- **Règle verrouillée pour raison légale (Art. 519 — sollicitation de mineurs ; Art. 521 — corruption de mineur, peines aggravées explicitement "dans les établissements d'enseignement" ; Art. 550 — harcèlement par communication électronique)** : toute conversation impliquant au moins un élève (seuil `<18 ans` **[Délégué]** — plus prudent que le seuil `<16 ans` utilisé pour le consentement d'inscription, car ces articles protègent le mineur au sens large, pas seulement le mineur non émancipé pour l'inscription) est journalisée de façon inaltérable côté serveur (une suppression par un participant ne fait que la masquer de son propre écran, jamais du stockage serveur) et consultable par l'A+ de l'établissement de l'élève sur signalement. Chaque message affiche un bouton "signaler" visible par tous les participants ; un signalement notifie immédiatement l'A+ concerné.
- Format V1 : texte uniquement, pas de pièce jointe ni d'image **[Délégué]** — élimine tout un pan de modération de contenu (nudité, contenu illicite) sans juger de sa valeur produit à ce stade ; s'ajoute plus tard si un vrai besoin apparaît.
- Pas de purge automatique des messages en V1 **[Délégué]** — cohérent avec la conservation à des fins de preuve/signalement ci-dessus, une purge affaiblirait la traçabilité légale qu'on vient de verrouiller.
- Notification par e-mail via Brevo à réception (même prestataire que le reste de la plateforme) **[Délégué]** — pas de nouveau canal à intégrer pour ce premier jet.

## UC-14 — Assistant IA pédagogique "El Professor"

> En tant qu'élève, je veux poser des questions à un assistant IA conversationnel sur le contenu d'un cours, afin d'obtenir des explications complémentaires à mon rythme, en dehors de la présence de l'enseignant.

- Basé exclusivement sur FreeLLM (jamais l'API Anthropic en direct — ADR-002).
- Contexte fourni au modèle : le `contenu_texte` du cours concerné (même source que la génération de quiz, UC-07).
- L'assistant ne donne jamais directement la réponse d'un devoir non encore soumis par l'élève (garde-fou de prompt) — cohérent avec l'esprit d'UC-08 (l'évaluation reste un exercice réel de l'élève).
- Aucune note, décision ou statut n'est produit par cet assistant (pas de décision automatisée à effet significatif — cohérent avec Art. 401, déjà appliqué ailleurs sur la plateforme).
- **Portée V1 : uniquement l'Élève, uniquement sur le contenu d'un cours donné [Délégué]** — c'est le cœur de l'idée d'origine (expliquer les cours à l'élève) et le périmètre le plus resserré possible à spécifier/tester. "Orienter chaque acteur selon son profil" (guide d'usage plateforme pour tuteur/enseignant/A+) est noté comme extension possible d'une Phase ultérieure, pas de cette UC — élargir la portée maintenant ferait de cette UC un produit différent (un assistant plateforme générique) avant même d'avoir validé la version pédagogique de base.
- Historique de conversation conservé par élève et par cours (pas de session éphémère) **[Délégué]** — utile à la continuité pédagogique d'une session à l'autre, cohérent avec le reste de la plateforme qui conserve l'historique (tentatives de quiz, soumissions).

---

# Phase 3

## UC-15 — Contenu vidéo/podcast pédagogique (asynchrone)

> En tant qu'enseignant, je veux publier un contenu vidéo ou podcast pour ma classe, afin d'enrichir mes cours au-delà des formats texte/PDF/audio déjà disponibles (UC-06).

- Extension directe d'UC-06 : mêmes règles de rattachement (classe/matière/chapitre, visible uniquement par les élèves inscrits pour l'année en cours), nouveau format `video` (mp4) en plus de `markdown`/`pdf`/`audio`.
- Stockage via LuluFiles (cohérent ADR-003), sauf si le format/poids vidéo dépasse ce que permet le plan LuluFiles actuel.
- **Limite hérité de la Phase 1, plan LuluFiles gratuit** (5 Go de transfert/mois, 2 Mo/s partagés — voir ADR-003) : plutôt que de changer de plan par anticipation, la limite de taille/durée par vidéo ci-dessous sert justement de garde-fou pour rester sous ce plafond en V1 **[Délégué]** ; passage à un plan payant seulement si la consommation réelle l'exige (pas de dépense anticipée sur une charge encore hypothétique).
- Taille/durée max par vidéo : 200 Mo / 15 minutes **[Délégué]**.

## UC-16 — Cours en direct (live)

> En tant qu'enseignant, je veux animer une session de cours en direct avec ma classe, afin de dispenser un enseignement interactif à distance en complément des contenus publiés.

- **Consentement renforcé (extension légale d'Art. 446, décision que je verrouille sur le fondement du même article que le consentement d'inscription)** : un élève mineur ne peut activer sa caméra/son micro en session live qu'après un consentement explicite et horodaté d'un tuteur couvrant spécifiquement "la participation avec image/voix à des sessions en direct" — distinct du consentement d'inscription générique (UC-01/UC-02), car il couvre un traitement d'image différent. Un élève sans ce consentement peut suivre la session en lecture seule (audio du professeur + chat texte), jamais bloqué hors de la classe.
- **Pas d'enregistrement automatique en V1 [Délégué, confirmé]**. Un enregistrement expose les élèves filmés à un traitement d'image supplémentaire (Art. 576 — atteinte à la représentation de la personne, en cas de diffusion sans autorisation) qui nécessiterait un consentement encore distinct de tous les tuteurs présents ce jour-là ; reporté hors V1 pour ne pas bloquer la fonctionnalité principale.
- Infrastructure technique de diffusion (WebRTC/SFU, fournisseur) — décision technique, pas une règle métier, tranchée à l'étape 3 (choix technique) une fois cette UC validée.
- Nombre max de participants simultanés par session : dépend du choix technique de l'étape 3, pas fixé ici.

## UC-17 — Billetterie d'événements scolaires

> En tant qu'A+ (ou "Parrain d'événement" désigné par lui), je veux créer un événement avec billetterie payante ou gratuite, afin d'organiser une manifestation ouverte aux familles (kermesse, remise de diplômes, spectacle).

- Champs : titre, description, lieu, date/heure, capacité max, prix par billet (0 si gratuit).
- Achat réservé aux utilisateurs authentifiés de la plateforme (élève, tuteur, enseignant, admin), pas d'achat anonyme par un public externe sans compte **[Délégué]** — cohérent avec le reste de la plateforme, évite de créer un parcours d'achat public entièrement distinct pour cette seule UC.
- Paiement Kkiapay, même mécanique que UC-10/UC-11/UC-12.
- Billet = référence unique scannée à l'entrée par un Contrôleur/Ticketeur désigné pour l'événement (rôle temporaire, comme UC-11/UC-12).
- **Remboursement (Art. 354, cohérent avec UC-11/UC-12)** : billet scanné à l'entrée → jamais remboursable. Avant l'événement, remboursable jusqu'à 48h avant **[Délégué]** (plus long qu'un ticket de transport/cantine, car un billet d'événement est en général acheté bien à l'avance).
- **Annulation de l'événement par l'organisateur (Art. 356 — résolution pour manquement contractuel)** : remboursement intégral obligatoire de tous les billets vendus, déclenché automatiquement à l'annulation.
- Tarif unique par événement en V1, pas de catégories de billets (adulte/enfant/famille) **[Délégué]** — une tarification par catégorie est une évolution indépendante, pas nécessaire pour valider le circuit de billetterie de base.

## UC-18 — Micro-jobs entre pairs avec séquestre

> En tant qu'utilisateur de la plateforme, je veux proposer ou accepter une mission rémunérée de courte durée (tutorat, petite mission de service), afin d'échanger un service contre rémunération de façon sécurisée par séquestre.

- 🔓 **Point administratif réel, hors périmètre de la loi n° 2017-20, donc pas couvert par la délégation légale** : l'âge minimum pour qu'un mineur perçoive une rémunération relève du Code du travail béninois, pas du droit numérique — je n'ai pas la compétence pour le trancher avec le skill `droit-numerique-benin`, et une décision produit ne peut pas se substituer à une confirmation juridique réelle sur ce point précis.
- **Décision de prudence en attendant cette confirmation [Délégué]** : en V1, seuls les rôles **majeurs par construction** (Enseignant, Tuteur, A+, A++) peuvent être client ou prestataire d'un micro-job. Le rôle Élève est exclu du dispositif dans son ensemble — y compris pour un élève par ailleurs majeur (≥18 ans), pour éviter d'avoir à calculer et vérifier un âge dynamique juste pour ce cas — jusqu'à ce que le point ci-dessus soit tranché administrativement ; l'UC sera réouverte pour élargir l'accès aux élèves à ce moment-là.
- Devenir prestataire ne nécessite pas de validation préalable par l'A+ **[Délégué]** — un compte Enseignant ou Tuteur déjà authentifié sur la plateforme peut publier une offre de mission directement, cohérent avec le faible enjeu d'une "petite mission" par rapport à un recrutement complet (UC-04).
- **Séquestre** : le paiement Kkiapay du client est retenu jusqu'à validation de la mission par le client ; le prestataire n'est payé qu'après. Mécanisme technique exact (Kkiapay porte-t-il lui-même la rétention, ou LuluSchools modélise-t-il un statut `retenu`/`libéré` de son côté) tranché à l'étape 3 une fois la documentation Kkiapay consultée — ce n'est pas une règle métier mais un détail d'intégration, cohérent avec le principe déjà verrouillé qu'LuluSchools n'héberge jamais les fonds elle-même (ADR-003).
- **Mécanisme de litige [Délégué]** : le client dispose de 5 jours après la déclaration de fin de mission par le prestataire pour la valider ou la contester (délai identique à UC-04b, cohérence de la plateforme) ; passé ce délai sans réaction, la mission est considérée validée tacitement et le paiement est libéré. En cas de contestation, l'A+ de l'établissement du prestataire tranche (accepté → paiement libéré, rejeté → remboursement du client), motif et horodatage conservés comme pour UC-04b.
- **Pas de commission de plateforme en V1 [Délégué]** — introduire une commission est une décision commerciale distincte de la validation du circuit fonctionnel de base ; le prestataire reçoit l'intégralité du montant convenu.

## UC-19 — Visite virtuelle 3D / vidéo aérienne (drone) d'un établissement

> En tant qu'A+ (ou A++), je veux publier une visite virtuelle 3D ou une vidéo aérienne de mon établissement, afin de le présenter à distance aux familles et futurs candidats.

- 🔓 **Point purement administratif, hors périmètre de la loi n° 2017-20, donc pas couvert par la délégation légale** : l'usage d'un drone relève de la réglementation aérienne béninoise (autorisation ANAC ou équivalent) — précondition opérationnelle à obtenir par l'établissement/A+ avant tout tournage. Traduit dans le produit par une case à cocher obligatoire ("j'atteste disposer des autorisations requises") avant publication, mais LuluSchools ne peut pas vérifier cette autorisation elle-même.
- **Droit à l'image (Art. 576 — atteinte à la représentation de la personne, en cas de diffusion sans autorisation) [Délégué]** : pas de floutage automatique en V1 (fiabilité insuffisante pour une garantie légale, faux négatifs possibles) et pas de recueil de consentement individuel par visage détecté (trop lourd à opérer pour la valeur ajoutée). À la place, la même case à cocher que ci-dessus engage l'établissement/A+ à ne publier que du contenu sans personne identifiable, ou pour lequel un consentement a déjà été recueilli hors plateforme — la responsabilité éditoriale reste celle de l'établissement, comme pour tout contenu qu'il publie ailleurs (affiches, site web).
- Format de diffusion : lien externe vers un service tiers (type Matterport) simplement référencé, pas d'upload natif via LuluFiles **[Délégué]** — évite tout traitement 3D/vidéo lourd côté LuluSchools et le risque de bande passante déjà signalé pour la vidéo (UC-15).

---

## État de validation — Phases 2 et 3 (2026-09-25)

Ce cahier des charges est **validé**. Historique des décisions pour garder la trace de qui a tranché quoi :

**Tranchées explicitement par l'utilisateur :**
1. Messagerie (UC-13) : DM adulte↔élève interdit, restreint au groupe de classe uniquement.
2. Toutes les autres décisions listées ci-dessous : déléguées explicitement ("je te fais confiance pour toutes les décisions légales et structurantes").

**Légalement tranchées (article cité — voir [[feedback-legal-autonomy]]) :**
3. Messagerie impliquant un élève : journalisation inaltérable + signalement obligatoire (Art. 519, 521, 550).
4. Tickets/billets déjà consommés ou scannés : jamais remboursables (Art. 354).
5. Annulation d'un événement par l'organisateur : remboursement intégral obligatoire (Art. 356).
6. Participation caméra/micro d'un mineur en session live : consentement tuteur distinct et explicite requis (extension d'Art. 446).

**Décisions produit déléguées (marquées `[Délégué]` dans chaque UC ci-dessus)** : heures/délais de remboursement, absence d'abonnement transport, absence de champ allergène, désignation du Contrôleur/Ticketeur par service, portée d'El Professor limitée à l'élève sur le cours, historique El Professor conservé, taille/durée max vidéo, absence d'enregistrement des lives, achat de billet réservé aux comptes authentifiés, tarif de billet unique, restriction des micro-jobs aux rôles majeurs par construction (Élève exclu du dispositif), pas de validation préalable A+ pour devenir prestataire, mécanisme de litige micro-job calqué sur UC-04b, pas de commission de plateforme, pas de floutage automatique pour les visites 3D/drone (attestation déclarative à la place), diffusion 3D par lien externe plutôt qu'upload natif.

**Restent de vrais points administratifs, hors portée d'une décision produit ou légale (pas bloquants pour l'UML/le contrat d'API, mais bloquants avant mise en production réelle de ces deux UC précises) :**
7. Micro-jobs (UC-18) : âge minimum légal pour qu'un mineur soit rémunéré — Code du travail béninois, hors loi n° 2017-20. Traité en attendant par l'exclusion totale du rôle Élève du dispositif (voir UC-18).
8. Visites 3D/drone (UC-19) : autorisation de vol de drone — réglementation aérienne (ANAC), hors loi n° 2017-20. Traité par une attestation déclarative de l'établissement (voir UC-19).
