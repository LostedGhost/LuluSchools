# LuluSchools — Diagrammes UML, Phases 2 et 3

Dérivés strictement de `docs/cas-utilisation-phase-2-3.md` (validé le 2026-09-25, étape 2 de la méthode `lucio-dev`). Mêmes conventions que `docs/diagrammes-uml-phase1.md` : numérotation UC continue dans le diagramme de cas d'utilisation (indépendante de la numérotation UC-11..UC-19 du document de spécification, rappelée en note), et plusieurs diagrammes de classes par cohérence de domaine plutôt qu'un seul diagramme géant (max ~15-20 nœuds chacun). En attente de validation explicite avant l'étape 3 (choix technique et contrat d'API).

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  Tuteur(["Tuteur"])
  Eleve(["Élève / Étudiant"])
  Enseignant(["Enseignant"])
  AdminEtab(["Admin établissement (A+)"])
  AdminMin(["Admin ministériel (A++)"])
  Controleur(["Contrôleur/Ticketeur «rôle temporaire»"])
  Kkiapay(["Kkiapay «system»"])
  FreeLLM(["FreeLLM «system»"])

  subgraph system["LuluSchools — Phases 2 et 3"]
    UC17(["Acheter un ticket de transport"])
    UC18(["Acheter un ticket de cantine"])
    UC19(["Valider un ticket/billet à l'entrée"])
    UC20(["Envoyer un message"])
    UC21(["Signaler un message"])
    UC22(["Consulter l'assistant El Professor"])
    UC23(["Publier un contenu vidéo/podcast"])
    UC24(["Animer un cours en direct"])
    UC25(["Participer à un cours en direct"])
    UC26(["Créer un événement avec billetterie"])
    UC27(["Acheter un billet d'événement"])
    UC28(["Proposer un micro-job"])
    UC29(["Réaliser et déclarer un micro-job"])
    UC30(["Contester une mission micro-job"])
    UC31(["Publier une visite virtuelle 3D/drone"])
  end

  Eleve --> UC17
  Tuteur --> UC17
  Eleve --> UC18
  Tuteur --> UC18
  Controleur --> UC19
  UC17 -.->|"«include»"| Kkiapay
  UC18 -.->|"«include»"| Kkiapay

  Tuteur --> UC20
  Eleve --> UC20
  Enseignant --> UC20
  AdminEtab --> UC20
  Eleve --> UC21
  Tuteur --> UC21
  UC21 -.->|"«extend»"| UC20

  Eleve --> UC22
  UC22 -.->|"«include»"| FreeLLM

  Enseignant --> UC23
  Enseignant --> UC24
  Eleve --> UC25
  UC24 -.->|"«include»"| UC25

  AdminEtab --> UC26
  Eleve --> UC27
  Tuteur --> UC27
  Enseignant --> UC27
  AdminEtab --> UC27
  Controleur --> UC19
  UC26 -.->|"«include»"| UC19
  UC27 -.->|"«include»"| Kkiapay

  Enseignant --> UC28
  Tuteur --> UC28
  Enseignant --> UC29
  Tuteur --> UC29
  Enseignant --> UC30
  Tuteur --> UC30
  UC30 -.->|"«extend»"| UC29
  UC28 -.->|"«include»"| Kkiapay

  AdminEtab --> UC31
  AdminMin --> UC31
```

Correspondance avec le document de spécification : UC17-18 = UC-11/UC-12, UC19 = validation commune aux tickets et billets (UC-11/UC-12/UC-17), UC20-21 = UC-13, UC22 = UC-14, UC23 = UC-15, UC24-25 = UC-16, UC26-27 = UC-17, UC28-30 = UC-18, UC31 = UC-19.

Notes :
- UC19 (validation à l'entrée) est un acteur/action partagé par les trois circuits de ticket (transport, cantine, billet d'événement) — c'est le même geste (scan) exercé par un Contrôleur/Ticketeur désigné séparément par service (voir UC-12 délégué).
- UC21 (signaler) étend UC20 : possible sur n'importe quel message, pas seulement ceux impliquant un mineur — mais la conséquence business (journalisation inaltérable, notification A+) ne s'applique qu'aux conversations avec un élève, voir le diagramme de classes messagerie.
- Le rôle Enseignant et le rôle Tuteur sont les deux seuls acteurs de UC28-30 (micro-jobs) — le rôle Élève est structurellement absent de ce sous-graphe, conformément à la restriction déléguée d'UC-18 (exclusion du dispositif en attendant confirmation légale sur l'âge minimum).
- UC26 (créer un événement) est réservé à l'A+ ; un "Parrain d'événement" désigné par lui agit avec les mêmes droits qu'un A+ sur cet événement précis — même principe de délégation que le Contrôleur/Ticketeur, pas un rôle RBAC distinct dans le modèle de données (voir diagramme de classes billetterie).

---

## Diagramme de classes — Tickets et billetterie

```mermaid
classDiagram
  class Utilisateur {
    <<abstract>>
    +id : UUID
  }
  class Etablissement {
    +codeEtablissement : string
  }
  class DesignationControleur {
    +service : string
    +dateDesignation : Date
  }
  class LigneTransport {
    +nom : string
    +prix : int
    +capacitePartrajet : int
  }
  class TicketTransport {
    +dateTrajet : Date
    +statut : string
    +prixPaye : int
  }
  class TypeRepasCantine {
    +nom : string
    +prix : int
    +capaciteParJour : int
  }
  class TicketCantine {
    +dateService : Date
    +statut : string
    +prixPaye : int
  }
  class Evenement {
    +titre : string
    +description : string
    +lieu : string
    +dateHeure : DateTime
    +capaciteMax : int
    +prixBillet : int
    +statut : string
  }
  class BilletEvenement {
    +referenceUnique : string
    +statut : string
    +prixPaye : int
  }
  class PaiementKkiapay {
    +transactionId : string
    +montant : int
    +statut : string
  }

  Etablissement "1" --> "0..*" LigneTransport : propose
  LigneTransport "1" --> "0..*" TicketTransport : vendu comme
  Utilisateur "1" --> "0..*" TicketTransport : achète
  Etablissement "1" --> "0..*" TypeRepasCantine : propose
  TypeRepasCantine "1" --> "0..*" TicketCantine : vendu comme
  Utilisateur "1" --> "0..*" TicketCantine : achète
  Etablissement "1" --> "0..*" Evenement : organise
  Utilisateur "1" --> "0..1" Evenement : parraine
  Evenement "1" --> "0..*" BilletEvenement : émet
  Utilisateur "1" --> "0..*" BilletEvenement : achète
  Etablissement "1" --> "0..*" DesignationControleur : désigne
  Utilisateur "1" --> "0..*" DesignationControleur : occupe
  DesignationControleur "0..1" --> "0..1" Evenement : rattachée à
  TicketTransport "0..1" --> "0..1" PaiementKkiapay : réglé par
  TicketCantine "0..1" --> "0..1" PaiementKkiapay : réglé par
  BilletEvenement "0..1" --> "0..1" PaiementKkiapay : réglé par
```

Note : `PaiementKkiapay` est une entité partagée par les trois circuits (transport, cantine, billetterie), même modèle que le paiement des actes académiques (UC-10, Phase 1) — un seul webhook Kkiapay pour tout le compte, le rattachement se fait via un identifiant de transaction, jamais une URL de webhook par objet. `DesignationControleur.service` prend les valeurs `transport`/`cantine`/`evenement`, cohérent avec la règle déléguée d'UC-12 (désignation séparée par service). `Evenement.parraine` par un Utilisateur est optionnel (0..1) : c'est l'A+ organisateur par défaut si aucun "Parrain d'événement" n'est désigné.

---

## Diagramme de classes — Messagerie et assistant pédagogique

```mermaid
classDiagram
  class Utilisateur {
    <<abstract>>
    +id : UUID
  }
  class Classe {
    +niveau : string
  }
  class Cours {
    +contenuTexte : string
  }
  class Conversation {
    +type : string
    +dateCreation : DateTime
  }
  class ParticipantConversation {
    +dateAjout : DateTime
  }
  class Message {
    +contenu : string
    +dateEnvoi : DateTime
    +masquePar : string
  }
  class SignalementMessage {
    +dateSignalement : DateTime
    +traite : bool
  }
  class SessionElProfessor {
    +dateCreation : DateTime
  }
  class MessageElProfessor {
    +role : string
    +contenu : string
    +dateEnvoi : DateTime
  }

  Classe "1" --> "1" Conversation : génère un groupe
  Conversation "1" --> "2..*" ParticipantConversation : réunit
  Utilisateur "1" --> "0..*" ParticipantConversation : participe via
  Conversation "1" --> "0..*" Message : contient
  Utilisateur "1" --> "0..*" Message : envoie
  Message "1" --> "0..1" SignalementMessage : peut faire l'objet de
  Utilisateur "1" --> "0..*" SignalementMessage : signale
  Utilisateur "1" --> "0..*" SessionElProfessor : ouvre
  Cours "1" --> "0..*" SessionElProfessor : porte sur
  SessionElProfessor "1" --> "0..*" MessageElProfessor : contient
```

Notes :
- `Conversation.type` prend les valeurs `dm`/`groupe_classe`. Une conversation `groupe_classe` est créée automatiquement à la création de la `Classe` (voir UC-13) ; `ParticipantConversation` y est ajouté/retiré automatiquement à chaque inscription/désinscription d'élève ou de rattachement d'enseignant.
- La restriction DM adulte↔élève (décidée explicitement par l'utilisateur) et la journalisation inaltérable pour toute conversation impliquant un élève (Art. 519/521/550) sont des règles de validation appliquées à la création de `ParticipantConversation`/`Message`, pas des attributs supplémentaires sur ces classes — elles se retrouveront dans le contrat d'API (étape 3) sous forme de contraintes RBAC, pas dans le modèle de données.
- `Message.masquePar` : liste des identifiants d'utilisateurs ayant masqué le message de leur côté (suppression non destructrice, voir UC-13 délégué) — jamais une suppression réelle de la ligne.
- `SessionElProfessor` est scoping par élève et par cours (portée V1 déléguée d'UC-14) : un élève a au plus une session par cours, réutilisée à chaque nouvelle question.

---

## Diagramme de classes — Contenu enrichi, cours en direct, visites virtuelles

```mermaid
classDiagram
  class Cours {
    +format : string
    +chapitre : string
  }
  class Classe {
    +niveau : string
  }
  class Enseignant {
    +id : UUID
  }
  class Eleve {
    +id : UUID
  }
  class Tuteur {
    +id : UUID
  }
  class SessionLive {
    +dateHeure : DateTime
    +statut : string
  }
  class ConsentementCameraLive {
    +dateConsentement : DateTime
    +donnePar : string
  }
  class ParticipationLive {
    +cameraActivee : bool
  }
  class Etablissement {
    +codeEtablissement : string
  }
  class VisiteVirtuelle {
    +type : string
    +lienExterne : string
    +attestationAutorisation : bool
  }

  Enseignant "1" --> "0..*" Cours : publie
  Cours "0..*" --> "1" Classe : rattaché à
  Enseignant "1" --> "0..*" SessionLive : anime
  SessionLive "0..*" --> "1" Classe : destinée à
  Eleve "1" --> "0..1" ConsentementCameraLive : couvert par
  Tuteur "1" --> "0..*" ConsentementCameraLive : donne
  Eleve "1" --> "0..*" ParticipationLive : participe via
  ParticipationLive "0..*" --> "1" SessionLive : rattachée à
  Etablissement "1" --> "0..*" VisiteVirtuelle : publie
```

Notes :
- `Cours.format` s'étend en Phase 3 avec la valeur `video` en plus de `markdown`/`pdf`/`audio` (UC-06 de la Phase 1, étendu par UC-15) — pas une nouvelle classe, une valeur d'énumération supplémentaire.
- `ParticipationLive.cameraActivee` ne peut être vrai que si un `ConsentementCameraLive` existe pour cet élève (contrôle applicatif, pas une contrainte de base de données représentable simplement) — sans consentement, l'élève participe quand même (`ParticipationLive` existe) mais en lecture seule (UC-16).
- Pas de classe `EnregistrementLive` : décision déléguée de ne pas enregistrer les sessions en V1 (UC-16).
- `VisiteVirtuelle.attestationAutorisation` matérialise la case à cochée par l'A+/A++ ("j'atteste disposer des autorisations requises" — drone ANAC, droit à l'image) décidée pour UC-19 ; ce n'est pas une vérification technique, seulement une trace d'engagement déclaratif.

---

## Diagramme de classes — Micro-jobs et séquestre

```mermaid
classDiagram
  class Utilisateur {
    <<abstract>>
    +id : UUID
  }
  class OffreMicroJob {
    +titre : string
    +description : string
    +prix : int
    +statut : string
  }
  class MissionMicroJob {
    +statut : string
    +dateDeclarationFin : DateTime
    +dateLimiteValidation : DateTime
  }
  class ContestationMicroJob {
    +motif : string
    +statut : string
    +decisionMotif : string
  }
  class PaiementKkiapay {
    +transactionId : string
    +montant : int
    +statut : string
  }

  Utilisateur "1" --> "0..*" OffreMicroJob : publie et paie comme client
  OffreMicroJob "1" --> "0..1" MissionMicroJob : donne lieu à
  Utilisateur "1" --> "0..*" MissionMicroJob : accepte comme prestataire
  MissionMicroJob "1" --> "0..1" ContestationMicroJob : peut faire l'objet de
  Utilisateur "1" --> "0..*" ContestationMicroJob : décide (A+)
  MissionMicroJob "1" --> "1" PaiementKkiapay : séquestré par
```

Notes :
- **Révision (2026-09-26, voir ADR-008 addendum)** : `Utilisateur.publie et paie comme client` est ouvert à **tous les rôles**, Élève inclus — payer pour un service ne pose pas de question d'âge minimum de travail. `Utilisateur.accepte comme prestataire` reste restreint par une règle applicative aux rôles Enseignant/Tuteur/A+/A++ — l'Élève en est exclu, cette fois parce que c'est le fait d'être **rémunéré** pour un travail qui pose la question légale (hors périmètre de la loi n° 2017-20), pas le fait de payer.
- `MissionMicroJob.statut` reprend le cycle délégué d'UC-18 : `en_cours` → `terminee_declaree` (le prestataire déclare la fin) → `validee` (tacite après 5 jours, ou explicite par le client) ou `contestee` → (si contestée) tranchée par un A+ via `ContestationMicroJob` → `payee`/`remboursee`.
- `PaiementKkiapay` réutilise la même entité que le diagramme billetterie (paiement partagé, un seul compte Kkiapay pour toute la plateforme) — le mécanisme exact de rétention (Kkiapay natif vs délai modélisé côté LuluSchools) reste à trancher à l'étape 3 une fois la documentation Kkiapay consultée, ce n'est pas une décision de modélisation mais un détail d'intégration technique.

---

## Points reportés à l'étape 3 (choix technique et contrat d'API)

Ces points ne bloquent pas la validation des diagrammes ci-dessus (aucune règle métier n'en dépend), mais devront être tranchés avant d'écrire le contrat d'API :
1. Mécanisme technique exact du séquestre Kkiapay (rétention native ou délai modélisé côté LuluSchools) — UC-18.
2. Infrastructure de diffusion du cours en direct (WebRTC/SFU, fournisseur) et nombre max de participants simultanés — UC-16.
3. Fournisseur/format exact de stockage vidéo compte tenu du plafond LuluFiles actuel (5 Go/mois) — UC-15.
