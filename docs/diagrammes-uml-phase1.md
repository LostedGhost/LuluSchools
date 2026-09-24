# LuluSchools — Diagrammes UML, Phase 1

Dérivés strictement de `cas-utilisation-phase-1.md` (étape 2 de la méthode `lucio-dev`). En attente de validation explicite avant de passer à l'étape 3 (choix technique et contrat d'API).

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  Tuteur(["Tuteur"])
  Eleve(["Élève / Étudiant"])
  Enseignant(["Enseignant"])
  AdminEtab(["Admin établissement (A+)"])
  AdminMin(["Admin ministériel (A++)"])
  Kkiapay(["Kkiapay «system»"])
  Certif(["Prestataire signature qualifiée «system»"])

  subgraph system["LuluSchools — Phase 1"]
    UC1(["Créer un compte tuteur"])
    UC2(["Inscrire un élève"])
    UC3(["Paramétrer poste ou campagne"])
    UC4(["Postuler à un poste enseignant"])
    UC5(["Contester un rejet de candidature"])
    UC6(["Signer le contrat électronique"])
    UC7(["Proposer une reconduction de contrat"])
    UC8(["Valider une proposition de coefficients"])
    UC9(["Publier un contenu pédagogique"])
    UC10(["Réaliser un quiz de progression"])
    UC11(["Soumettre un devoir"])
    UC12(["Corriger un devoir"])
    UC13(["Consulter moyennes et bulletin"])
    UC14(["Valider passage, redoublement ou diplôme"])
    UC15(["Soumettre une demande d'acte académique"])
    UC16(["Traiter une demande d'acte académique"])
  end

  Tuteur --> UC1
  Tuteur --> UC2
  Eleve --> UC2
  Eleve --> UC10
  Eleve --> UC11
  Eleve --> UC13
  Tuteur --> UC13
  Eleve --> UC15
  Tuteur --> UC15
  AdminEtab --> UC3
  AdminEtab --> UC5
  AdminEtab --> UC7
  AdminEtab --> UC8
  AdminEtab --> UC16
  AdminMin --> UC8
  Enseignant --> UC4
  Enseignant --> UC5
  UC5 -.->|"«extend»"| UC4
  Enseignant --> UC6
  UC6 -.->|"«include»"| Certif
  UC7 -.->|"«include»"| UC6
  Enseignant --> UC9
  Enseignant --> UC12
  Enseignant --> UC14
  UC16 -.->|"«include»"| Kkiapay
```

Notes : UC5 (« contester ») étend UC4, ce n'est pas un chemin systématique. UC6 (signature) inclut toujours le prestataire de certification qualifiée. UC7 (reconduction) inclut UC6 : proposer une reconduction aboutit toujours à une nouvelle signature complète. UC16 inclut Kkiapay uniquement pour les types de demande payants (délivrance d'actes), pas pour la réclamation gratuite.

## Diagramme de classes — Identité, inscriptions, recrutement, contrats

```mermaid
classDiagram
  class Utilisateur {
    <<abstract>>
    +id : UUID
    +nom : string
    +prenom : string
    +telephone : string
    +email : string
  }
  class Tuteur {
    +pieceIdentite : string
  }
  class Eleve {
    +dateNaissance : Date
    +matricule : string
    +statutInscription : string
  }
  class Enseignant {
    +cvUrl : string
  }
  class AdminEtablissement {
    <<A+>>
  }
  class AdminMinisteriel {
    <<A++>>
  }
  class Etablissement {
    +codeEtablissement : string
    +type : string
    +statut : string
  }
  class Classe {
    +niveau : string
    +capacite : int
    +politiqueDepassement : string
  }
  class Inscription {
    +statut : string
    +dateDemande : Date
    +consentementParentalHorodatage : DateTime
  }
  class Candidature {
    +score : float
    +statut : string
  }
  class DocumentCandidature {
    +type : string
    +noteIA : float
    +seuilRequis : float
    +coefficient : float
  }
  class VerificationCasierJudiciaire {
    +statut : string
    +dateVerification : Date
  }
  class Contestation {
    +motif : string
    +statut : string
  }
  class Contrat {
    +syllabus : string
    +dateSignature : DateTime
    +dureeConservation : int
  }
  class PropositionReconduction {
    +statut : string
  }

  Utilisateur <|-- Tuteur
  Utilisateur <|-- Eleve
  Utilisateur <|-- Enseignant
  Utilisateur <|-- AdminEtablissement
  Utilisateur <|-- AdminMinisteriel
  Tuteur "1" --> "0..*" Eleve : représente
  Eleve "1" --> "0..*" Inscription : soumet
  Inscription "0..*" --> "1" Classe : demande
  Classe "0..*" --> "1" Etablissement : appartient à
  AdminEtablissement "1" --> "1" Etablissement : administre
  Enseignant "0..*" --> "0..*" Etablissement : rattaché à
  Enseignant "1" --> "0..*" Candidature : dépose
  Candidature "0..*" --> "1" Etablissement : cible
  Candidature "1" --> "1..*" DocumentCandidature : comprend
  Candidature "1" --> "0..1" VerificationCasierJudiciaire : inclut
  Candidature "1" --> "0..1" Contestation : peut faire l'objet de
  Candidature "1" --> "0..1" Contrat : aboutit à
  Contrat "1" --> "0..1" PropositionReconduction : peut générer
```

Note : `VerificationCasierJudiciaire` est volontairement une entité séparée de `DocumentCandidature` (accès restreint, pas de note IA, conservation courte — voir UC-04 sur le régime Art. 395).

## Diagramme de classes — Pédagogie, évaluations, actes académiques

```mermaid
classDiagram
  class Eleve {
    +matricule : string
  }
  class Enseignant {
    +id : UUID
  }
  class Classe {
    +niveau : string
  }
  class Etablissement {
    +codeEtablissement : string
  }
  class Cours {
    +format : string
    +chapitre : string
  }
  class Quiz {
    +seuilReussite : float
  }
  class Devoir {
    +dateLimite : DateTime
    +bareme : string
  }
  class Soumission {
    +dateSoumission : DateTime
    +note : float
    +statut : string
  }
  class ReferentielCoefficient {
    +matiere : string
    +coefficient : float
    +valideParMinistere : bool
  }
  class Bulletin {
    +periode : string
    +moyenneGenerale : float
    +decisionPassage : string
  }
  class DemandeActeAcademique {
    +type : string
    +statut : string
    +montant : int
  }

  Enseignant "1" --> "0..*" Cours : publie
  Cours "0..*" --> "1" Classe : rattaché à
  Cours "0..1" --> "0..*" Quiz : contient
  Enseignant "1" --> "0..*" Devoir : crée
  Devoir "0..*" --> "1" Classe : assigné à
  Eleve "1" --> "0..*" Soumission : dépose
  Soumission "0..*" --> "1" Devoir : répond à
  Enseignant "1" --> "0..*" Soumission : corrige
  Classe "0..*" --> "0..*" ReferentielCoefficient : applique
  Eleve "1" --> "0..*" Bulletin : reçoit
  Bulletin "0..*" --> "0..*" ReferentielCoefficient : calculé avec
  Eleve "1" --> "0..*" DemandeActeAcademique : soumet
  DemandeActeAcademique "0..*" --> "1" Etablissement : traitée par
```

`Eleve`, `Enseignant`, `Classe` et `Etablissement` sont partagés avec le premier diagramme de classes — deux vues du même modèle pour rester lisible (max ~15-20 nœuds par diagramme), pas deux modèles distincts.
