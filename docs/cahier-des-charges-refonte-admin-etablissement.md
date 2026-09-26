# Refonte du portail Admin Établissement (A+) — Cahier des charges

> **Version** : 1.1 | **Date** : 2026-09-26 | **Statut** : **Validé** — diagrammes UML faits (`docs/diagrammes-uml-phase-6-admin-etablissement.md`, contrat d'API fusionné, `filiere` révisé en texte libre après relecture de `seed_mega.py`), passage direct au backend

Ce document couvre les 6 points soumis pour le profil A+, structurés en **6 lots** (numérotés 6.1 à 6.6, UC-39 à UC-58). Il propose aussi un **ordre de dépendance** entre lots, car un point structurant transverse (l'année académique) conditionne plusieurs des demandes. Les décisions ambiguës sont tranchées et marquées **[Délégué]**. Le Lot 6.6 (micro-jobs/marketplace) reflète l'arbitrage explicite de l'utilisateur du 2026-09-26, qui corrige la première proposition de ce document.

---

## 0. Le fil conducteur : l'année académique comme dimension manquante

Constat d'audit avant de commencer : **rien dans le schéma actuel ne modélise l'année académique**. `Classe` est une table plate (niveau/capacité/politique de dépassement), `Inscription` n'a pas de champ année. Une classe « 6ème A » n'existe qu'une fois, pour toujours — il n'y a aucune notion de rentrée, de reconduction, ni de bascule d'année. Or trois des six demandes en dépendent directement (rentrée/reconduction de classes, vie scolaire multi-années, console de filtrage par année). **[Délégué]** : plutôt que de traiter ça en silo dans chaque lot, l'année académique devient une dimension de premier ordre dès le Lot 6.2, et tous les autres lots la réutilisent — c'est le seul moyen d'éviter de la réinventer trois fois avec des formats différents.

---

## Lot 6.1 — Rentrée scolaire & Vie scolaire

### UC-39 — Déclarer la rentrée
En tant qu'A+, je veux ouvrir une campagne de rentrée pour une année académique donnée (ex. « 2027-2028 »), afin de rendre l'établissement inscriptible pour cette année.
- Règle : nouvelle entité `RentreeScolaire` (établissement, année académique, statut ouverte/fermée) — une seule rentrée ouverte à la fois par établissement.

### UC-40 — Inviter les tuteurs à (ré)inscrire
En tant qu'A+, je veux notifier les tuteurs des élèves déjà connus de mon établissement (inscrits une année précédente, quel que soit le statut) que la rentrée est ouverte, afin de faciliter la réinscription.
- **[Délégué]** : « inviter » = envoi d'un e-mail (réutilise `BrevoEmailClient`, déjà en place) listant les enfants concernés + lien direct vers la réinscription. Pas de nouveau canal de notification (pas de SMS/push) — cohérent avec le seul canal déjà utilisé sur toute la plateforme.

### UC-41 — Consulter la vie scolaire d'un élève/étudiant
En tant qu'A+, je veux consulter l'historique complet d'un élève/étudiant (inscriptions passées, établissements fréquentés, notes, bulletins) dès que mon établissement a reçu **au moins une demande d'inscription** de sa part, afin de prendre une décision d'admission informée — même si cette demande a été rejetée ou concerne une autre année.
- Règle **[Délégué]** : « a reçu une demande » = il existe un enregistrement `Inscription` liant cet `Eleve` à une `Classe` de mon établissement, quel que soit son statut. C'est un droit de lecture **permanent** une fois acquis (comme un dossier de transfert scolaire réel — voir recherche § annexe), pas révocable par l'élève. Cohérent avec la pratique documentée (une fois qu'un dossier est dans le système d'un établissement, il y reste accessible pour cet établissement).
- Portée de lecture : toutes les `Inscription` de cet élève (tous établissements), tous ses `Bulletin`, et les établissements fréquentés — **jamais** en écriture, uniquement en lecture, et jamais les données d'un autre élève.
- Nouvel endpoint : `GET /eleves/{id}/vie-scolaire`, réservé à un A+ qui remplit la condition ci-dessus (vérifiée serveur, pas seulement cachée côté UI) ou à un A++.

### UC-42 — Photo conditionnée au statut étudiant/élève
La vie scolaire n'affiche la photo que si l'élève est un **étudiant** (inscrit dans un établissement de type UP), jamais s'il est un **élève** (EP/ES).
- **[Délégué]** : « étudiant » n'est pas une nouvelle colonne — dérivé de `Etablissement.type == UP` sur sa dernière inscription validée, exactement comme `AGE_MAJORITE_NUMERIQUE`/marketplace dérive déjà l'éligibilité sans dupliquer l'information. Aucune photo n'existe d'ailleurs nulle part sur `Eleve` aujourd'hui : nouveau champ optionnel `photo_lulufiles_id`, upload réservé à l'élève/étudiant lui-même (jamais imposé par un tiers), LuluFiles (ADR-003).

---

## Lot 6.2 — Classes enrichies, reconduction, console multi-modules

### UC-43 — Créer une classe adaptée au type d'établissement
En tant qu'A+, je veux que le formulaire de création de classe s'adapte au type de mon établissement :
- **EP/ES (maternelle → lycée)** : niveau en select fermé (Maternelle PS/MS/GS, CP...CM2, 6ème...Terminale — taxonomie déjà utilisée par `seed_mega.py`, désormais formalisée en énumération plutôt que texte libre) + filière/section optionnelle en select (A, B, C... — partage de niveau, pas une filière académique).
- **UP (supérieur)** : niveau en select fermé (1ère/2ème/3ème année Licence, 1ère/2ème année Master...) + filière **obligatoire** parmi le référentiel de filières de l'établissement (Droit, Génie Civil, Informatique de Gestion... — même taxonomie que `seed_mega.py`).
- Capacité (déjà existant) + **année académique** (nouveau, cf. § 0).
- **[Délégué]** : les taxonomies niveau/filière deviennent des énumérations gérées (pas du texte libre) pour permettre le select — source unique : extraction de la taxonomie déjà écrite en dur dans `seed_mega.py`, reprise telle quelle plutôt que réinventée.

### UC-44 — Reconduire les classes d'une année sur l'autre
En tant qu'A+, je veux dupliquer la structure de mes classes (niveau, filière, capacité) vers une nouvelle année académique en un geste (action groupée), afin de ne pas les recréer une à une chaque rentrée.
- Règle : duplique la **structure**, jamais les élèves (une classe reconduite démarre vide — les inscriptions sont un acte annuel explicite, UC-39/40).

### UC-45 — Fiche classe : élèves par défaut, pivot sur l'objet et l'année
En cliquant une classe, l'A+ voit par défaut les élèves inscrits pour l'année académique en cours, avec une ligne de sélecteurs : **année académique** (historique inclus) et **objet à afficher** (élèves, enseignants affectés, tuteurs concernés, matières/cours, devoirs, moyennes/notes globales).
- Réutilise le composant `DataTable` (Phase 5) — tri/pagination/recherche/filtre déjà génériques.

### UC-46 — Console de filtrage à l'échelle de l'établissement
Le même écran doit permettre de retirer le filtre « classe » et de voir l'objet choisi pour **tout l'établissement**, toujours en datatable paginé.
- **[Délégué]** : un seul écran (`ConsoleEtablissementPage`), pas deux — le filtre classe est optionnel (vide = tout l'établissement), l'objet et l'année restent les deux axes de pivot. Nouveaux endpoints agrégés par objet, filtrables par `etablissement_id` + `classe_id?` + `annee_academique?`, pagination serveur systématique (même règle que Phase 5).

---

## Lot 6.3 — Recrutement : formulaire dynamique

### UC-47 — Publier une offre détaillée avec formulaire configurable
En tant qu'A+, je veux rédiger une annonce complète (description, matière recherchée, montant ou tranche prévisionnelle du contrat) et configurer un formulaire de candidature sur mesure (champs texte court/long, fichier, choix, etc. — à la Google Forms), afin d'obtenir exactement l'information dont j'ai besoin pour ce poste précis.
- Règle **[Délégué]** : nouveau champ JSON `schema_formulaire` sur `Poste` (liste de `{id, label, type, requis, options?}`) — pattern JSON-schema-driven déjà standard (voir recherche § annexe), stocké backend, rendu dynamique côté frontend. Le système de critères de notation IA existant (`CritereDocumentPoste`) reste **en parallèle**, inchangé : il note les documents, le nouveau formulaire collecte l'information contextuelle (montant souhaité, disponibilité, etc.) — deux mécanismes complémentaires, pas une fusion qui casserait le scoring IA déjà validé.

### UC-48 — Postuler via le formulaire exact défini
L'enseignant remplit exactement les champs définis par l'établissement pour ce poste (en plus de l'upload de documents déjà existant, inchangé).
- Nouveau : `reponses_formulaire` JSON sur `Candidature`, validé serveur contre `schema_formulaire` du poste (types, champs requis).

### UC-49 — Consulter les candidatures avec leurs réponses
La liste des candidatures d'un poste affiche les réponses au formulaire dynamique en plus des documents/scores déjà existants, en datatable.

---

## Lot 6.4 — Actes académiques : formulaire dynamique + livraison du document

### UC-50 — Configurer un type d'acte avec formulaire dynamique
Réutilise **exactement** le moteur de formulaire du Lot 6.3 (`schema_formulaire` sur `TypeActeAcademique` au lieu de `pieces_requises` en texte libre) — un seul moteur, deux usages, cohérent avec le principe « pas de logique dupliquée ».

### UC-51 — Soumettre une demande via ce formulaire
Le tuteur/étudiant remplit le formulaire exact (`reponses_formulaire` sur `DemandeActeAcademique`), y compris l'upload de pièces si le type de champ choisi est « fichier ».
- Ceci **résout l'écart déjà documenté** dans `backend/PROJECT_MAP.md` (§ actes) : « aucune pièce jointe possible » — le champ de type fichier du formulaire dynamique couvre ce besoin sans bascule JSON→multipart risquée sur l'endpoint existant (le formulaire dynamique gère nativement le mélange texte/fichier).

### UC-52 — Livrer le document une fois la demande traitée
En tant qu'A+, une fois la demande acceptée, je téléverse (ou le système génère, si un gabarit existe) le document final, afin que le demandeur puisse le télécharger.
- **[Délégué]** : livraison = upload manuel par l'A+ dans ce premier lot (pas de génération automatique de PDF officiel avec sceau — hors périmètre, nécessiterait un gabarit par établissement et une décision de mise en page que l'utilisateur n'a pas donnée). Nouveau champ `document_final_lulufiles_id` sur `DemandeActeAcademique`.

### UC-53 — Télécharger l'acte prêt
Le tuteur/étudiant télécharge le document dès que `document_final_lulufiles_id` est renseigné (lien signé LuluFiles, même pattern que les autres fichiers de la plateforme).

---

## Lot 6.5 — Ticketerie unifiée avec QR codes

### UC-54 — Ticket PDF avec QR code (transport / cantine / billetterie)
Chaque ticket acheté (`TicketTransport`, `TicketCantine`, `BilletEvenement`) génère un PDF avec un QR code encodant son identifiant, afin d'être présenté et scanné sans ressaisie.
- Règle **[Délégué]** : un **seul module partagé** `app/modules/ticketerie/` génère le PDF+QR pour les 3 types de tickets existants (pas 3 implémentations dupliquées) — le QR encode un jeton signé (HMAC, même famille que les OTP déjà en place), pas l'UUID brut, pour empêcher qu'un ticket soit forgé en devinant un id. Nouvelle dépendance `qrcode` (génération) + `reportlab` (mise en page PDF minimale : logo, infos du ticket, QR).

### UC-55 — Scanner un ticket par QR (en plus de la saisie manuelle)
`ValiderAccesPage` gagne un mode « scanner » (caméra du navigateur) en plus de la saisie manuelle déjà existante — le scan décode le jeton et appelle exactement le même endpoint de validation déjà en place, aucun nouveau chemin serveur.
- Nouvelle dépendance frontend légère de lecture QR côté caméra (pattern standard, pas de service tiers).

### UC-56 — Déléguer la création d'événement / le contrôle
Formaliser ce qui existe déjà en pièces détachées (`parrain_utilisateur_id` sur `Evenement`, `DesignationControleur` pour transport/cantine/billetterie) en un seul écran de délégation côté A+, afin qu'il n'ait pas à connaître 3 mécanismes différents pour une même idée.
- **[Délégué]** : pas de fusion de modèle de données (le pattern actuel fonctionne et distingue correctement « parrain d'un événement précis » de « contrôleur désigné d'un service ») — uniquement une unification **d'écran**, pas de schéma.

---

## Lot 6.6 — Micro-jobs et marketplace : les étudiants gagnent de l'argent, les élèves EP/ES n'y entrent pas

**Tranché par l'utilisateur (2026-09-26)**, corrige la première proposition de ce document : les adultes (Enseignant/Tuteur/A+/A++) gardent l'accès aux micro-jobs — seuls les élèves EP/ES en sont exclus. Mais puisque les micro-jobs sont pensés comme un moyen pour les **étudiants** de se faire de l'argent de poche, les adultes ne doivent plus pouvoir **répondre** à une offre (rôle PRESTATAIRE, celui qui est rémunéré) — ils peuvent en revanche continuer à **publier et payer** une offre (rôle CLIENT, celui qui embauche).

### UC-57 — Micro-jobs : CLIENT ouvert aux adultes + étudiants, PRESTATAIRE réservé aux étudiants
- **CLIENT** (publie une offre, paie) : Enseignant, Tuteur, Admin_établissement, Admin_ministériel, **Étudiant** (élève inscrit et validé dans un établissement de type UP — même dérivation qu'UC-42). **Élève EP/ES exclu.**
- **PRESTATAIRE** (accepte une offre, est rémunéré) : **Étudiant uniquement.** Les adultes (Enseignant/Tuteur/A+/A++), auparavant seuls rôles majeurs autorisés côté prestataire (ADR-008 addendum), en sont désormais exclus — cohérent avec l'objectif : les micro-jobs sont un revenu d'appoint étudiant, pas un service que les adultes de la plateforme se rendraient entre eux.
- Ceci **révise** (et ne remplace pas entièrement) l'ADR-008 addendum : le principe « CLIENT ouvert largement / PRESTATAIRE restreint » reste vrai, seule la composition du groupe restreint change (adultes → étudiants).

### UC-58 — Marketplace réservée aux étudiants (achat et vente)
La marketplace reste strictement étudiant↔étudiant (aucun rôle adulte n'y a jamais eu accès, rien ne change de ce côté) : la restriction actuelle (« élève ≥16 ans du même établissement ») devient « étudiant du même établissement » au sens UC-42 — dérivée du type d'établissement (UP) plutôt que de la seule condition d'âge, resserrement cohérent avec le nom déjà donné à la fonctionnalité depuis la Phase 4 (« marketplace étudiante »).

---

## Priorisation et dépendances

| Lot | Dépend de | Priorité |
|---|---|---|
| 6.2 (classes + année académique) | — (fondation) | **P0 — à faire en premier** |
| 6.1 (rentrée + vie scolaire) | 6.2 (année académique) | P0 |
| 6.6 (restriction étudiants) | 6.2 (dérivation étudiant/élève déjà utilisée en 6.1) | P1 — rapide une fois 6.1/6.2 faits |
| 6.3 (recrutement dynamique) | — (indépendant) | P1 |
| 6.4 (actes dynamique) | 6.3 (réutilise le même moteur de formulaire) | P1 |
| 6.5 (ticketerie QR) | — (indépendant) | P2 |

**[Délégué]** : proposition de commencer par **6.2 puis 6.1**, parce que trois autres points du cahier des charges (la console multi-modules, la vie scolaire, et indirectement la restriction étudiants) reposent sur la notion d'année académique et la dérivation étudiant/élève — les construire dans le désordre obligerait à les refaire.

---

## Annexe — recherche

- Formulaires dynamiques : pattern JSON-schema-driven (type/label/validators par champ, stocké backend, rendu frontend) — [Building Dynamic Forms with JSON Schema](https://peterullrich.com/build-dynamic-forms-with-json-schemas), [SurveyJS](https://surveyjs.io/stay-updated/blog/dynamically-create-forms-from-json-schema).
- Billetterie QR : jeton unique par ticket, scan marque « utilisé », toute réutilisation détectée — [QR Ticketing System](https://github.com/sarthaklambaa/QR_Ticketing_System).
- Portabilité du dossier scolaire : une fois le dossier reçu par un établissement (même via transfert), il reste consultable pour cet établissement ; les dossiers permanents couvrent notes, présence, établissements fréquentés — pratique documentée dans les systèmes scolaires réels, cohérente avec la règle déléguée UC-41.
