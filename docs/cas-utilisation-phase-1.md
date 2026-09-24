# LuluSchools — Cas d'utilisation, Phase 1 (socle)

Rédigé selon la méthode `lucio-dev` (pipeline spec-first). Chaque cas d'utilisation liste ses règles métier précises ; les points encore ouverts sont marqués 🔓. Ce document doit être explicitement validé comme complet avant de passer à l'étape 2 (diagrammes UML).

Cadrage : mandat ministériel officiel, premier déploiement au Bénin, conformité suivie sur la loi n° 2017-20 (skill `droit-numerique-benin`). Paiement/séquestre via Kkiapay.

## Acteurs (rappel RBAC)

A++ (admin ministériel, actif) · A+ (admin établissement, actif) · A- (admin/décideur passif, lecture seule) · P (enseignant) · Élève/Étudiant · Tuteur (parent/représentant légal) · Contrôleur/Ticketeur (rôle temporaire) · Prestataire micro-job / Parrain d'événement.

---

## UC-01 — Création de compte tuteur

> En tant que parent/représentant légal, je veux créer un compte tuteur, afin de pouvoir suivre la scolarité de mon enfant et donner mon consentement à son inscription.

- Champs : nom, prénom, e-mail (obligatoire, unique), mot de passe, téléphone (optionnel, gardé pour un usage futur — tickets/notifications).
- 🔓 Mot de passe : proposition par défaut — au moins 8 caractères, une majuscule, un chiffre (à confirmer ou ajuster).
- Vérification de l'e-mail par code à 6 chiffres avant activation du compte (**changement** : e-mail plutôt que SMS — envoi via Brevo, voir `choix-technique-phase1.md`). Code valide 10 minutes, 5 tentatives maximum avant invalidation.
- Un tuteur peut être rattaché à plusieurs élèves.
- Tout consentement donné pour un élève mineur est horodaté et stocké de façon consultable (Art. 389-390 — le responsable du traitement doit pouvoir démontrer le consentement).

## UC-02 — Inscription d'un élève

> En tant que tuteur (ou élève lui-même s'il a 16 ans ou plus), je veux inscrire un élève à un établissement pour l'année scolaire en cours, afin qu'il accède aux services de la plateforme.

- Champs : nom, prénom, date de naissance, établissement demandé, niveau/classe demandé.
- **Branche d'âge (Art. 446)** : élève < 16 ans → inscription à l'état `en_attente_consentement_parental` jusqu'à validation explicite d'un tuteur rattaché. Élève ≥ 16 ans → il valide seul (un tuteur peut être associé en lecture seule, non bloquant).
- Postulation limitée à la capacité d'accueil déclarée par l'établissement, par classe/groupe pédagogique.
- Dépassement de capacité : chaque établissement configure sa propre politique par campagne (ordre d'arrivée du dossier complet / notes-concours / tirage au sort), choisie par l'A+ à l'ouverture de la campagne.
- Statuts : `soumise` → `en_attente_consentement_parental` (si applicable) → `validée` (matricule généré) → `rejetée` (motif obligatoire, notifié).

## UC-03 — Génération du matricule

> En tant que système, je veux générer un matricule unique à la validation d'une inscription, afin d'identifier l'élève de façon pérenne dans le système éducatif national.

- 🔓 Format provisoire par défaut : `BJ-[CODE_ETABLISSEMENT:4]-[ANNEE_ENTREE:4]-[SEQUENCE:5]` (ex. `BJ-EP12-2026-00347`). **En attente de la nomenclature officielle à fournir par l'utilisateur.**
- Code établissement attribué une seule fois par le ministère (A++) à la création de l'établissement.
- Le matricule est conservé à vie, y compris en cas de changement d'établissement (reconduction, jamais régénéré).

## UC-04 — Candidature enseignant

> En tant qu'enseignant candidat, je veux postuler à un poste ouvert par un établissement, afin d'être recruté et de signer un contrat.

- Dépôt : CV, diplômes, pièce d'identité, casier judiciaire (formats PDF/JPG, 5 Mo max par défaut — paramètre configurable).
- Chaque document déposé, **hors casier judiciaire**, est noté sur 100 par un modèle d'IA selon les critères du poste.
- Score final du candidat = moyenne pondérée de ces notes réelles, par coefficient de document (coefficients + seuils minimaux fixés par l'A+, par poste).
- Un candidat sous le seuil minimal d'un document est éliminé, indépendamment de son score global.
- Si aucun candidat n'atteint les seuils, le poste reste `non pourvu` et génère une alerte à l'A+.
- **Casier judiciaire — régime à part (Art. 395)** : vérifié séparément, hors pipeline IA générique. Accès réservé aux personnes désignées par l'A+, engagement de confidentialité signé (Art. 402). Seul un statut `conforme`/`non conforme` + date de vérification est conservé durablement ; le document brut est supprimé automatiquement 30 jours après la décision finale de recrutement. *Point administratif ouvert : le ministère doit confirmer le texte réglementaire fondant cette vérification.*
- Un enseignant peut être rattaché à plusieurs établissements simultanément (comptes/contrats/syllabus distincts par établissement).

## UC-04b — Contestation du rejet d'une candidature

> En tant que candidat enseignant rejeté (score sous seuil, ou casier jugé non conforme), je veux contester la décision, afin qu'elle soit réexaminée par un humain avant d'être définitive.

- Fondement : Art. 401 — pas de décision 100% automatisée à effet significatif sans recours possible.
- Délai de contestation : 5 jours ouvrés à compter de la notification du rejet.
- L'A+ (ou un jury désigné) réexamine et rend une décision : `contestation acceptée` (le candidat réintègre le classement) ou `contestation rejetée` (motif obligatoire, notifié).
- Le poste peut continuer d'être pourvu en parallèle avec d'autres candidats ; une contestation acceptée après coup priorise le candidat sur un poste équivalent encore ouvert, sans annuler un contrat déjà signé.
- Motif et horodatage de la décision conservés (traçabilité en cas de recours ultérieur devant l'APDP, Art. 448).

## UC-05 — Signature du contrat électronique

> En tant qu'enseignant retenu, je veux signer électroniquement mon contrat intégrant le syllabus imposé, afin que ma relation contractuelle et ma base de rémunération soient actées.

- Relecture complète du contrat et du syllabus possible avant signature, avec droit de renoncer avant confirmation finale (Art. 343-344).
- Signature électronique **qualifiée** dès la V1 (Art. 285-287) — nécessite un prestataire de certification agréé Bénin/CEDEAO à identifier (point opérationnel, pas une ambiguïté de spec).
- Accusé de réception généré, envoyé à l'enseignant et à l'établissement.
- Contrat conservé 10 ans (Art. 346).
- Le contrat est re-signé intégralement chaque année — pas de reconduction tacite.

## UC-05b — Proposition de reconduction de contrat

> En tant qu'A+, je veux proposer la reconduction du contrat d'un enseignant déjà en poste, afin de simplifier son renouvellement annuel sans repasser par un recrutement complet.

- Déclenchable par l'A+ dans une fenêtre avant l'échéance du contrat en cours (défaut : 30 jours avant la fin, paramètre configurable).
- Syllabus et rémunération ajustables par rapport à l'année précédente avant envoi.
- L'enseignant doit re-signer intégralement (signature qualifiée) — aucun renouvellement automatique sans action explicite de sa part.
- Sans réponse ou en cas de refus avant la fin du contrat en cours, le poste redevient disponible et repasse par un recrutement classique (UC-04).

## UC-06 — Publication d'un contenu pédagogique

> En tant qu'enseignant, je veux publier un contenu de cours (texte enrichi, PDF, ou audio) pour ma classe, afin que mes élèves y accèdent depuis la plateforme.

- Formats V1 : Markdown enrichi (images), PDF (visionneuse intégrée, pas de téléchargement forcé), audio (mp3/wav).
- Taille max 50 Mo par fichier par défaut (paramètre configurable).
- Contenu rattaché à une classe/matière/chapitre précis, visible uniquement par les élèves inscrits à cette classe pour l'année en cours.

## UC-07 — Progression séquentielle (déblocage de chapitre)

> En tant qu'élève, je veux accéder au chapitre suivant seulement après avoir réussi le quiz du chapitre en cours, afin de suivre une progression structurée.

- Seuil de réussite configurable par l'enseignant (défaut 80%).
- Tentatives illimitées.

## UC-08 — Soumission et correction d'un devoir

> En tant qu'élève, je veux soumettre mon devoir avant la date limite, afin qu'il soit corrigé par mon enseignant.

- Verrouillage strict à l'échéance. Absence de soumission → note zéro automatique, **sans dérogation possible** (règle sans exception, aucun justificatif accepté pour réouvrir le dépôt).

> En tant qu'enseignant, je veux corriger un devoir selon un barème rigide (binaire, auto-corrigé) ou flexible (évaluation manuelle), afin de noter mes élèves.

- Type de barème choisi par l'enseignant à la création de l'évaluation, non modifiable après la première soumission d'un élève.

## UC-09 — Calcul des moyennes et bulletin

> En tant que système, je veux calculer automatiquement la moyenne d'un élève selon les coefficients (primaire/secondaire) ou crédits (supérieur) en vigueur, afin de générer son bulletin.

- Coefficients/crédits fixés par le ministère (A++) ; l'établissement (A+) peut proposer une mise à jour, effective seulement après validation ministérielle.
- Le calcul est automatique et immédiat pour affichage à l'élève/tuteur.
- Toute décision à conséquence lourde qui en découle (passage en classe supérieure, redoublement, délivrance de diplôme) reste soumise à validation humaine (conseil de classe / jury) — jamais actée uniquement par le calcul automatique (cohérence avec l'esprit de l'Art. 401).

## UC-10 — Demande dans le circuit des actes académiques

> En tant qu'élève (ou tuteur), je veux soumettre une demande relevant du circuit des actes académiques — réclamation de note ou délivrance d'un acte officiel (bulletin, attestation, diplôme) — afin d'obtenir une correction ou un document officiel.

- **Catalogue d'actes configurable par établissement** (révision suite à un exemple réel de barème universitaire — IFRI) : plutôt qu'une liste figée de types, chaque établissement (A+) définit son propre catalogue de `TypeActeAcademique` : nom (ex. "Attestation de succès", "Attestation d'admissibilité", "Attestation de diplôme et diplôme", "Supplément au diplôme", "Certification de copie"), prix (0 si gratuit), liste de pièces justificatives requises (texte libre, ex. acte de naissance, CIP, relevés de notes, quittance de paiement), et une condition d'éligibilité optionnelle en texte libre (ex. "délivrée uniquement aux étudiants ayant validé toutes les unités d'enseignement, ou ayant soutenu leur mémoire"). Un même acte peut avoir une partie payante et une partie gratuite (ex. l'attestation de diplôme est payante, le diplôme lui-même est gratuit) — modélisé comme deux lignes de catalogue distinctes plutôt qu'un seul type ambigu.
- `réclamation_note` reste un type particulier, toujours gratuit, hors catalogue configurable (référence obligatoire à l'évaluation contestée + motif).
- Une demande d'acte (`DemandeActeAcademique`) référence un type du catalogue, fournit les pièces justificatives requises (upload via LuluFiles) et, si le type est payant, la preuve de paiement Kkiapay avant traitement.
- Statuts communs : `soumise` → `en_traitement` (service compétent de l'établissement, A+, qui vérifie aussi les pièces fournies et l'éligibilité) → `traitée` (acceptée avec document/correction produite, ou rejetée avec motif obligatoire).
- 🔓 Délai de recevabilité d'une réclamation de note — proposition par défaut : recevable jusqu'à la clôture officielle du bulletin de la période concernée. À confirmer.

---

## Points encore ouverts avant validation finale de la Phase 1

1. Nomenclature officielle du matricule élève (UC-03) — à fournir par l'utilisateur.
2. Prestataire de certification pour la signature électronique qualifiée (UC-05) — action opérationnelle.
3. Texte réglementaire couvrant la vérification du casier judiciaire pour le recrutement enseignant (UC-04) — action ministérielle.
4. Délai de recevabilité d'une réclamation de note (UC-10) — confirmer la proposition par défaut.
