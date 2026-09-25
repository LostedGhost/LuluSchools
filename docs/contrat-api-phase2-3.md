# LuluSchools — Contrat d'API, Phases 2 et 3

Dérivé strictement de `docs/cas-utilisation-phase-2-3.md` (validé) et `docs/diagrammes-uml-phase2-3.md` (validé), étape 3 de la méthode `lucio-dev`. Mêmes conventions que `docs/contrat-api-phase1.md` (base `/api/v1`, JWT Bearer, pagination `?page=&page_size=`, enveloppe d'erreur `{"error": {...}}`, upload multipart + lien signé pour les fichiers) — non dupliquées ici.

**UC-18 (micro-jobs + séquestre) suit le modèle "Option A" décidé dans `docs/adr/ADR-008-kkiapay-pas-de-versement-tiers.md`** : le séquestre est un statut suivi par LuluSchools, pas un mécanisme Kkiapay natif — le reversement au prestataire est déclenché manuellement par un opérateur humain en V1 (voir tableau ci-dessous), en attendant une confirmation du support Kkiapay sur `setup_payout` qui pourrait automatiser cette dernière étape sans changer le contrat observable.

## Tickets de transport (UC-11)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/etablissements/{id}/lignes-transport` | A+ | Crée une ligne : `nom`, `prix`, `capacite_par_trajet` |
| GET | `/etablissements/{id}/lignes-transport` | tout utilisateur authentifié | Catalogue des lignes actives |
| POST | `/lignes-transport/{id}/tickets` | Élève, ou Tuteur pour un enfant rattaché | `date_trajet` ; refusé (`409`) si la capacité de la ligne pour cette date est atteinte (compte les tickets `achete`/`valide`) ; statut initial `achete` |
| POST | `/tickets-transport/{id}/paiement/amorcer` | propriétaire du ticket | Même mécanique que UC-10 : enregistre le `transaction_id` Kkiapay obtenu côté client |
| POST | `/tickets-transport/{id}/valider` | Contrôleur désigné sur cette ligne | Scan à l'embarquement, `achete` → `valide` ; refusé si `date_trajet` déjà passée sans validation (`expire`, voir job ci-dessous) ou déjà `rembourse` |
| POST | `/tickets-transport/{id}/rembourser` | propriétaire du ticket | Refusé (`409`) si déjà `valide`, ou si moins de 24h avant `date_trajet` (délai délégué UC-11 : veille 18h) |
| GET | `/tickets-transport/{id}` | propriétaire, A+ de l'établissement de la ligne, ou Contrôleur désigné | Lecture |
| GET | `/mes-tickets-transport` | Élève, ou Tuteur (ses enfants) | Historique |

Un ticket non validé dont `date_trajet` est dépassée passe `expire` (job périodique ou calcul à la volée en lecture, pas de nouvelle table — décision technique laissée à l'implémentation).

## Tickets de cantine (UC-12)

Même structure qu'UC-11, entités et endpoints renommés :

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/etablissements/{id}/types-repas-cantine` | A+ | `nom`, `prix`, `capacite_par_jour` |
| GET | `/etablissements/{id}/types-repas-cantine` | tout utilisateur authentifié | Catalogue |
| POST | `/types-repas-cantine/{id}/tickets` | Élève, ou Tuteur pour un enfant rattaché | `date_service` ; mêmes règles de capacité qu'UC-11 |
| POST | `/tickets-cantine/{id}/paiement/amorcer` | propriétaire | idem UC-11 |
| POST | `/tickets-cantine/{id}/valider` | Contrôleur désigné sur ce service | idem UC-11 |
| POST | `/tickets-cantine/{id}/rembourser` | propriétaire | idem UC-11 |
| GET | `/tickets-cantine/{id}` | propriétaire, A+, Contrôleur | Lecture |
| GET | `/mes-tickets-cantine` | Élève, ou Tuteur (ses enfants) | Historique |

## Désignation de Contrôleur/Ticketeur (partagé UC-11/UC-12/UC-17)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/etablissements/{id}/controleurs` | A+ | `utilisateur_id`, `service` (`transport`\|`cantine`\|`evenement`), `evenement_id` (obligatoire seulement si `service=evenement`) — une désignation par service (délégué UC-12), un même utilisateur peut cumuler plusieurs désignations distinctes |
| GET | `/etablissements/{id}/controleurs` | A+ | Liste des désignations actives |
| DELETE | `/controleurs/{id}` | A+ qui a créé la désignation | Révoque (rôle temporaire par nature) |

## Messagerie (UC-13)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| GET | `/conversations` | tout utilisateur authentifié | Mes conversations (DM + groupes de classe dont je suis membre), triées par dernier message |
| POST | `/conversations` | tout utilisateur authentifié | `participant_id`, crée (ou récupère si existe déjà) un DM. **Refusé (`403`)** si l'appelant est Enseignant/A+/A++ et que `participant_id` est un compte Élève — restriction verrouillée par l'utilisateur (2026-09-25), message d'erreur oriente vers le groupe de classe. Une exception : un Tuteur peut ouvrir un DM avec un Élève qui lui est rattaché (`403` sinon, anti-IDOR) |
| GET | `/classes/{id}/conversation` | membre de la classe (enseignant rattaché, élève inscrit, tuteur rattaché) | Le groupe de classe, créé automatiquement à la création de la `Classe` (aucun endpoint de création manuelle) |
| GET | `/conversations/{id}/messages` | participant de la conversation | Pagination standard, plus récents en premier |
| POST | `/conversations/{id}/messages` | participant de la conversation | `contenu` (texte, pas de pièce jointe — délégué UC-13) ; si un participant est Élève, le message est journalisé de façon inaltérable (Art. 519/521/550) |
| DELETE | `/messages/{id}` | participant de la conversation du message | Suppression non destructrice (oubliée du premier jet du contrat) : masque le message du point de vue de l'appelant uniquement (`masque_par`), jamais du stockage serveur — la journalisation pour preuve/signalement reste intacte |
| POST | `/messages/{id}/signaler` | tout participant de la conversation du message | Rend le signalement visible à l'A+ concerné via `GET /etablissements/{id}/signalements` (écran de revue, même logique que les autres écrans de révision de la plateforme) |
| GET | `/etablissements/{id}/signalements` | A+ | Signalements non traités pour les élèves de son établissement |
| POST | `/signalements/{id}/traiter` | A+ | Marque traité, `decision` en texte libre conservée |

## Assistant IA "El Professor" (UC-14)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/cours/{id}/el-professor/session` | Élève inscrit à la classe du cours | Crée la session si elle n'existe pas encore pour cet élève+ce cours (upsert), sinon la retourne |
| GET | `/cours/{id}/el-professor/session` | Élève propriétaire | Session + historique des échanges |
| POST | `/el-professor/sessions/{id}/messages` | Élève propriétaire | `question` (texte) → appel **synchrone** à FreeLLM (contexte = `cours.contenu_texte` + historique de la session), retourne la réponse immédiatement — synchrone comme la génération de quiz (UC-07), pas de raison de différer une réponse de chat interactif en arrière-plan (contrairement à la notation/correction, ADR-005, qui n'a pas de contrainte d'interactivité immédiate) |

## Contenu vidéo/podcast (UC-15)

**Pas de nouvel endpoint** : extension directe de `POST /classes/{id}/cours` (UC-06, Phase 1) — le champ `format` accepte désormais aussi `video`, avec une limite serveur de 200 Mo / 15 minutes (délégué UC-15) vérifiée à l'upload, `413`/`422` sinon. Le reste du cycle de vie (rattachement classe/matière/chapitre, visibilité) est inchangé.

## Cours en direct (UC-16)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/classes/{id}/sessions-live` | Enseignant rattaché à la classe | `date_heure`, statut initial `planifiee` |
| GET | `/classes/{id}/sessions-live` | membre de la classe | Liste (à venir et passées) |
| POST | `/sessions-live/{id}/demarrer` | Enseignant organisateur | `planifiee` → `en_cours`, retourne les informations de connexion (détail dépendant du fournisseur retenu à l'implémentation, voir ADR à écrire séparément pour ce choix technique) |
| POST | `/eleves/{id}/consentement-camera-live` | Tuteur de l'élève concerné | Consentement explicite et horodaté, distinct du consentement d'inscription (extension d'Art. 446) — condition pour que cet élève puisse activer sa caméra/micro en session live |
| POST | `/sessions-live/{id}/rejoindre` | Élève inscrit à la classe | Retourne le token de connexion ; `camera_autorisee` reflète l'existence d'un consentement pour cet élève — sans consentement, l'élève rejoint quand même en lecture seule (jamais bloqué hors de la classe) |
| POST | `/sessions-live/{id}/terminer` | Enseignant organisateur | `en_cours` → `terminee`. Pas d'enregistrement produit (délégué UC-16) |

## Billetterie d'événements (UC-17)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/etablissements/{id}/evenements` | A+ | `titre`, `description`, `lieu`, `date_heure`, `capacite_max`, `prix_billet` (0 si gratuit) |
| POST | `/evenements/{id}/parrain` | A+ organisateur | Désigne un `utilisateur_id` comme "Parrain d'événement" — mêmes droits de gestion que l'A+ sur cet événement précis uniquement (pas un rôle RBAC global) |
| GET | `/etablissements/{id}/evenements` | tout utilisateur authentifié | Catalogue |
| GET | `/evenements/{id}` | tout utilisateur authentifié | Lecture |
| POST | `/evenements/{id}/annuler` | A+ organisateur ou Parrain désigné | `statut` → `annule`, déclenche automatiquement le remboursement intégral de tous les billets vendus (Art. 356) |
| POST | `/evenements/{id}/billets` | tout utilisateur authentifié | Refusé (`409`) si `capacite_max` atteinte ; statut initial `achete` |
| POST | `/billets/{id}/paiement/amorcer` | propriétaire du billet | idem UC-10/UC-11 |
| POST | `/billets/{id}/valider` | Contrôleur désigné pour cet événement | Scan à l'entrée, `achete` → `valide` |
| POST | `/billets/{id}/rembourser` | propriétaire du billet | Refusé si déjà `valide`, ou moins de 48h avant `date_heure` (délégué UC-17) |
| GET | `/mes-billets` | tout utilisateur authentifié | Historique |

## Visites virtuelles 3D / drone (UC-19)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/etablissements/{id}/visites-virtuelles` | A+, A++ | `type` (`3d`\|`drone`), `lien_externe` (pas d'upload natif — délégué UC-19), `attestation_autorisation` obligatoirement `true` (`422` sinon) — atteste des autorisations réglementaires (drone/ANAC) et du droit à l'image, engagement déclaratif de l'établissement, pas une vérification technique |
| GET | `/etablissements/{id}/visites-virtuelles` | tout utilisateur authentifié | Catalogue, y compris pour un public non-inscrit consultant la page de l'établissement |
| DELETE | `/visites-virtuelles/{id}` | A+, A++ de l'établissement | Retrait |

## Micro-jobs et séquestre (UC-18)

Rôles autorisés à publier une offre (prestataire) ou l'accepter (client) : Enseignant, Tuteur, A+, A++ — le rôle Élève est structurellement exclu (délégué UC-18), aucune vérification d'âge dynamique n'est nécessaire.

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/micro-jobs/offres` | Enseignant, Tuteur, A+, A++ | `titre`, `description`, `prix` ; statut initial `ouverte` |
| GET | `/micro-jobs/offres` | Enseignant, Tuteur, A+, A++ | Liste des offres `ouverte` |
| GET | `/micro-jobs/offres/{id}` | Enseignant, Tuteur, A+, A++ | Lecture |
| POST | `/micro-jobs/offres/{id}/accepter` | Enseignant, Tuteur, A+, A++ (autre que le prestataire) | Refusé (`409`) si l'offre n'est plus `ouverte` ; crée la `MissionMicroJob` (statut `en_cours`), offre passe `fermee` |
| POST | `/missions-micro-job/{id}/paiement/amorcer` | client de la mission | Même mécanique `paiement/amorcer` que UC-10/UC-11/UC-17 : le compte Kkiapay unique de LuluSchools encaisse le prix. Le "séquestre" est purement un statut suivi par LuluSchools (Option A, ADR-008) — Kkiapay ne sait pas qu'il s'agit d'un séquestre |
| POST | `/missions-micro-job/{id}/declarer-fin` | prestataire de la mission | `en_cours` → `terminee_declaree`, fixe `date_limite_validation` = +5 jours |
| POST | `/missions-micro-job/{id}/valider` | client de la mission | `terminee_declaree` → `validee` (validation explicite) ; passé `date_limite_validation` sans action, un job périodique (ou calcul à la volée en lecture) considère la mission `validee` tacitement (délégué UC-18) |
| POST | `/missions-micro-job/{id}/contester` | client de la mission | Uniquement avant `date_limite_validation`, `terminee_declaree` → `contestee` |
| POST | `/contestations-micro-job/{id}/decision` | A++ | `acceptee` (mission → `remboursee`, paiement rendu au client) ou `rejetee` (motif obligatoire, mission → `validee`) — même schéma que UC-04b. **Correction du premier jet du contrat** : arbitré par l'A++ (ministériel), pas "l'A+ de l'établissement du prestataire" comme écrit initialement — un micro-job n'est rattaché à aucun établissement (marketplace plateforme entière, voir `docs/diagrammes-uml-phase2-3.md`) et un Tuteur prestataire n'a de toute façon aucun établissement à résoudre |
| POST | `/missions-micro-job/{id}/reverser-prestataire` | A++ | Autorisé seulement si `statut=validee` (cohérent avec l'arbitrage A++ ci-dessus, plutôt qu'un rôle d'exploitation distinct non spécifié). Reversement manuel hors Kkiapay (mobile money direct vers le prestataire) ; `reference_paiement` (texte libre, preuve) obligatoire pour passer `validee` → `payee`. Point d'automatisation potentiel une fois `setup_payout` confirmé auprès du support Kkiapay (voir ADR-008) |
| GET | `/mes-missions-micro-job` | Enseignant, Tuteur, A+, A++ | Historique, comme prestataire et comme client |

---

## Points laissés à l'implémentation (étape 4), sans impact sur ce contrat

- Fournisseur/infra de diffusion pour `POST /sessions-live/{id}/demarrer` (WebRTC/SFU hébergé) — détail interne à la réponse de l'endpoint, pas sa forme.
- Job de passage `achete` → `expire` pour les tickets/billets non validés après leur date (UC-11/UC-12/UC-17) : calcul à la volée en lecture vs tâche planifiée — n'affecte pas le contrat observable.
- Job de validation tacite des missions micro-job après `date_limite_validation` (UC-18) : même remarque.
- Avant de coder `POST /missions-micro-job/{id}/reverser-prestataire` (UC-18), contacter le support Kkiapay (support@kkiapay.me) pour confirmer si `setup_payout` peut automatiser ce reversement ponctuel — voir ADR-008. Si oui, l'implémentation change, pas le contrat.
