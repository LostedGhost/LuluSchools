# LuluSchools — Diagrammes UML, Phase 6 (Admin établissement A+)

Dérivés strictement de `docs/cahier-des-charges-refonte-admin-etablissement.md` (validé le 2026-09-26, y compris la correction utilisateur sur UC-57/58). Contrat d'API fusionné dans ce même document (comme pour la Phase 5, à la demande explicite de l'utilisateur). Numérotation UC continue depuis `docs/diagrammes-uml-phase-5-admin-ministeriel.md` (dernier numéro utilisé : UC54) — indépendante de la numérotation UC-39..UC-58 du cahier des charges, correspondance donnée en note sous chaque diagramme.

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  AdminEtab(["Admin établissement (A+)"])
  Tuteur(["Tuteur"])
  Eleve(["Élève / Étudiant"])
  Enseignant(["Enseignant"])
  Controleur(["Contrôleur désigné «rôle délégué»"])

  subgraph lot1["Lot 6.1 — Rentrée & vie scolaire"]
    UC55(["Déclarer la rentrée"])
    UC56(["Inviter les tuteurs à (ré)inscrire"])
    UC57(["Consulter la vie scolaire d'un élève/étudiant"])
  end
  subgraph lot2["Lot 6.2 — Classes & console"]
    UC58(["Créer une classe (niveau/filière/année selon le type d'établissement)"])
    UC59(["Reconduire des classes vers une nouvelle année"])
    UC60(["Consulter la fiche d'une classe (pivot année × objet)"])
    UC61(["Consulter la console établissement (tous objets, toutes classes)"])
  end
  subgraph lot3["Lot 6.3/6.4 — Formulaires dynamiques"]
    UC62(["Configurer le formulaire d'un poste"])
    UC63(["Postuler via le formulaire du poste"])
    UC64(["Configurer le formulaire d'un type d'acte"])
    UC65(["Soumettre une demande d'acte via formulaire"])
    UC66(["Livrer le document final d'un acte traité"])
    UC67(["Télécharger l'acte prêt"])
  end
  subgraph lot4["Lot 6.5 — Ticketerie QR"]
    UC68(["Télécharger un ticket PDF avec QR"])
    UC69(["Valider un ticket par scan QR ou id manuel"])
    UC70(["Déléguer créateur d'événement / contrôleur"])
  end

  AdminEtab --> UC55
  UC56 -.->|"«include»"| UC55
  AdminEtab --> UC56
  AdminEtab --> UC57

  AdminEtab --> UC58
  UC59 -.->|"«extend»"| UC58
  AdminEtab --> UC59
  AdminEtab --> UC60
  UC61 -.->|"«extend»"| UC60
  AdminEtab --> UC61

  AdminEtab --> UC62
  Enseignant --> UC63
  UC63 -.->|"«include»"| UC62
  AdminEtab --> UC64
  Tuteur --> UC65
  Eleve --> UC65
  UC65 -.->|"«include»"| UC64
  AdminEtab --> UC66
  Tuteur --> UC67
  Eleve --> UC67
  UC67 -.->|"«extend»"| UC66

  Eleve --> UC68
  Controleur --> UC69
  AdminEtab --> UC70
  UC69 -.->|"«extend»"| UC70
```

Correspondance : UC55=UC-39, UC56=UC-40, UC57=UC-41/42, UC58=UC-43, UC59=UC-44, UC60=UC-45, UC61=UC-46, UC62=UC-47, UC63=UC-48/49, UC64=UC-50, UC65=UC-51, UC66=UC-52, UC67=UC-53, UC68=UC-54, UC69=UC-55, UC70=UC-56. **UC-57/58 du cahier des charges (restriction micro-jobs/marketplace) n'a aucun nœud** : ce n'est pas une nouvelle action mais une révision RBAC sur des cas d'utilisation déjà diagrammés en Phase 2/3 (« Proposer un micro-job », « Réaliser et déclarer un micro-job ») et Phase 4 (marketplace) — traité en note ci-dessous, pas en diagramme.

Notes :
- « Élève / Étudiant » reste un seul acteur RBAC (`RoleUtilisateur.ELEVE`) — étudiant/élève est une distinction **dérivée** (type d'établissement de la dernière inscription validée), jamais un rôle séparé.
- UC69 (valider par scan) étend UC70 (délégation) au sens où le contrôleur qui valide est nécessairement quelqu'un désigné via UC70 — pas une nouvelle règle, celle-ci existe déjà (Phase 2/3, `DesignationControleur`).
- **Révision RBAC micro-jobs (UC-57 du cahier des charges, pas de nœud dédié)** : sur les use cases déjà diagrammés en Phase 2/3 (`UC28 Proposer un micro-job`, `UC29 Réaliser et déclarer un micro-job`), l'acteur associé au rôle PRESTATAIRE (celui qui accepte/est rémunéré) passe de {Enseignant, Tuteur} à {Élève-étudiant uniquement} ; le rôle CLIENT (publier/payer) reste ouvert à {Enseignant, Tuteur, Élève-étudiant}, `Élève` (EP/ES) désormais explicitement exclu des deux côtés (il ne l'était déjà pas côté client en pratique, la restriction est maintenant explicite plutôt qu'absente).
- **Révision RBAC marketplace (UC-58, pas de nœud dédié)** : la restriction déjà existante en Phase 4 (« élève ≥16 ans ») devient « étudiant » (dérivé, pas d'âge) — aucun autre changement de son diagramme de classes Phase 4.

---

## Diagramme de classes — Année académique, classes, rentrée, vie scolaire

```mermaid
classDiagram
  class Etablissement {
    +type : string
  }
  class RentreeScolaire {
    +anneeAcademique : string
    +statut : string
  }
  class Classe {
    +niveau : string
    +filiere : string
    +anneeAcademique : string
    +capacite : int
  }
  class Eleve {
    +nom : string
    +prenom : string
    +photoLuluFilesId : string
  }
  class Inscription {
    +statut : string
  }
  class Bulletin {
    +periode : string
    +moyenneGenerale : float
  }

  Etablissement "1" --> "0..*" RentreeScolaire : declare
  Etablissement "1" --> "0..*" Classe : possede (par annee)
  Classe "0..1" --> "0..1" Classe : reconduite_vers (annee suivante)
  Classe "1" --> "0..*" Inscription : recoit
  Eleve "1" --> "0..*" Inscription : soumet (tous etablissements)
  Eleve "1" --> "0..*" Bulletin : possede (via classes frequentees)
```

Notes :
- `RentreeScolaire` : nouvelle table, une seule `statut=ouverte` par établissement à la fois (contrainte applicative, pas une contrainte SQL — cohérent avec le reste du projet qui privilégie les vérifications applicatives explicites plutôt que les contraintes DB opaques).
- `Classe.anneeAcademique` (nouveau, non nul) et `Classe.filiere` (nouveau, nullable) : **`filiere` reste un texte libre, pas une énumération globale** — décision révisée par rapport au cahier des charges initial après relecture de `seed_mega.py` : les filières université sont propres à chaque établissement (pool de programmes différent par établissement), les sections EP/ES (A/B/C) sont arbitraires par établissement. Une énumération figée serait fausse dès le premier établissement hors norme. **`niveau` reste également une colonne texte** côté base (aucune migration de type nécessaire), mais le **frontend** propose un `<select>` fermé dont les options dépendent de `Etablissement.type` (taxonomie reprise telle quelle de `seed_mega.py` : Maternelle/CI/CP/CE1-CM2 pour EP, 6ème-Terminale + séries pour ES, licence/master pour UP) — cohérent avec le principe déjà appliqué aux référentiels (Phase 5) : guider la saisie sans rigidifier le schéma.
- `Classe "reconduite_vers"` : pas une vraie FK avec contrainte forte, un champ `reconduite_depuis_id` nullable sur `Classe` suffit à tracer l'origine d'une reconduction (UC-44), sans verrouiller la structure si une classe est reconduite manuellement/partiellement modifiée.
- `Eleve.photoLuluFilesId` (nouveau, nullable) : upload réservé au titulaire du compte (élève/étudiant lui-même), jamais imposé par un tiers — LuluFiles (ADR-003), résolu à la demande (même pattern que les photos d'établissement, jamais en masse).
- Aucune nouvelle table pour la « vie scolaire » (UC-41) : c'est une **vue agrégée en lecture** sur `Inscription`/`Bulletin`/`Classe`/`Etablissement` déjà existants, exposée par un nouvel endpoint avec une règle d'accès dédiée (contrat § plus bas) — pas un nouveau modèle de données.

---

## Diagramme de classes — Formulaire dynamique (recrutement + actes académiques)

```mermaid
classDiagram
  class Poste {
    +titre : string
    +description : string
    +matiere : string
    +remunerationMin : float
    +remunerationMax : float
    +schemaFormulaire : json
  }
  class Candidature {
    +reponsesFormulaire : json
  }
  class TypeActeAcademique {
    +nom : string
    +schemaFormulaire : json
  }
  class DemandeActeAcademique {
    +reponsesFormulaire : json
    +documentFinalLuluFilesId : string
  }
  class ChampFormulaire {
    <<value object, pas une table>>
    +id : string
    +label : string
    +type : string
    +requis : bool
    +options : string[]
  }

  Poste "1" --> "0..*" ChampFormulaire : schemaFormulaire contient
  Poste "1" --> "0..*" Candidature : recoit
  TypeActeAcademique "1" --> "0..*" ChampFormulaire : schemaFormulaire contient
  TypeActeAcademique "1" --> "0..*" DemandeActeAcademique : encadre
```

Notes :
- **Un seul moteur, deux usages** : `ChampFormulaire` n'est pas une table — c'est la forme d'un élément du JSON `schema_formulaire` (`{id, label, type: "texte_court"|"texte_long"|"fichier"|"choix_unique"|"choix_multiple", requis, options?}`), stockée telle quelle sur `Poste`/`TypeActeAcademique`, validée côté Pydantic à l'écriture. Un fichier téléversé pour un champ `type="fichier"` va sur LuluFiles, seul l'id est stocké dans `reponses_formulaire` (même pattern que toutes les pièces jointes de la plateforme).
- `Poste.description`/`matiere`/`remunerationMin`/`remunerationMax` (nouveaux, `remunerationMax` nullable si montant fixe plutôt que tranche) : complètent l'annonce, **indépendants** de `CritereDocumentPoste` (notation IA des documents, inchangé) et de `schemaFormulaire` (collecte d'information contextuelle) — trois mécanismes qui coexistent sans se chevaucher.
- `DemandeActeAcademique.documentFinalLuluFilesId` (nouveau, nullable) : résout l'écart déjà documenté (aucune livraison de document) — renseigné par l'A+ au traitement (UC-52), condition de téléchargement (UC-53).
- `TypeActeAcademique.pieces_requises` (texte libre existant) reste tel quel pour compatibilité descriptive, mais n'est plus le mécanisme de collecte — remplacé par `schemaFormulaire` pour toute nouvelle demande.

---

## Diagramme de classes — Ticketerie QR (transport / cantine / billetterie)

```mermaid
classDiagram
  class TicketTransport {
    +statut : string
  }
  class TicketCantine {
    +statut : string
  }
  class BilletEvenement {
    +statut : string
  }
  class JetonTicket {
    <<value object, calcule a la volee>>
    +type : string
    +ticketId : UUID
  }

  TicketTransport ..> JetonTicket : encode en QR
  TicketCantine ..> JetonTicket : encode en QR
  BilletEvenement ..> JetonTicket : encode en QR
```

Notes :
- **Aucune nouvelle colonne, aucune nouvelle table.** Le jeton QR est calculé à la demande : `"{type}:{id}"` (ex. `"transport:e8735c1a-..."`) — l'UUID du ticket est déjà cryptographiquement non devinable (128 bits aléatoires), une signature HMAC supplémentaire (envisagée dans le cahier des charges initial) ajouterait de la complexité sans bénéfice de sécurité réel ici. **Simplification décidée en design, après relecture des endpoints `valider_ticket_transport`/`valider_ticket_cantine`/`valider_billet` déjà existants** : ils prennent déjà l'id du ticket en paramètre de route, exactement ce qu'un scan QR ou une saisie manuelle fournit — aucun nouvel endpoint de validation n'est nécessaire, seuls la génération du PDF+QR et le mode caméra côté frontend sont neufs.
- Nouveau module partagé `app/modules/ticketerie/` : une seule fonction de génération PDF+QR paramétrée par type, réutilisée par les 3 endpoints `GET .../pdf`.

---

## Points tranchés directement ici (fusion de l'étape 3 — contrat d'API)

Convention commune : `motif`/traçabilité non requis pour ce lot (pas de nouveau pouvoir destructeur ministériel — le journal d'audit Phase 5 reste dédié à l'A++, ce lot est un mandat d'établissement ordinaire). Pagination serveur obligatoire sur toute liste potentiellement large (même règle qu'ADR-009/Phase 5).

| # | Méthode & route | UC | Notes |
|---|---|---|---|
| 1 | `POST /etablissements/{id}/rentrees` | UC55 | `{annee_academique}` — A+/A++, ferme automatiquement toute rentrée déjà ouverte pour cet établissement |
| 2 | `GET /etablissements/{id}/rentrees` | UC55 | Historique des rentrées |
| 3 | `POST /etablissements/{id}/rentrees/{rentree_id}/inviter-tuteurs` | UC56 | E-mail aux tuteurs des élèves déjà connus (inscription précédente, tout statut) |
| 4 | `GET /eleves/{id}/vie-scolaire` | UC57 | A+ **seulement si** une `Inscription` existe entre cet élève et son établissement (vérifié serveur) ; A++ sans restriction. Renvoie inscriptions + bulletins + établissements fréquentés ; `photo_url` seulement si dernière inscription validée pointe vers un établissement `type=UP` |
| 5 | `POST /etablissements/{id}/classes` *(existant, payload étendu)* | UC58 | `+ filiere?, annee_academique` |
| 6 | `GET /etablissements/{id}/classes` *(existant, réponse enrichie + filtre)* | UC58 | `?annee_academique=` optionnel (défaut : rentrée ouverte ou année courante) |
| 7 | `POST /etablissements/{id}/classes/reconduire` | UC59 | `{classe_ids: [], nouvelle_annee: str}` → duplique structure (jamais les élèves) |
| 8 | `GET /etablissements/{id}/console/eleves` | UC60/61 | `?classe_id=&annee_academique=&q=&limit=&offset=` |
| 9 | `GET /etablissements/{id}/console/enseignants` | UC60/61 | `?classe_id=&annee_academique=&limit=&offset=` (via `AffectationEnseignant`) |
| 10 | `GET /etablissements/{id}/console/tuteurs` | UC60/61 | `?classe_id=&annee_academique=&limit=&offset=` (tuteurs des élèves en portée) |
| 11 | `GET /etablissements/{id}/console/cours` | UC60/61 | `?classe_id=&annee_academique=&limit=&offset=` (équivalent A+ du `GET /admin/cours` Phase 5, scope établissement) |
| 12 | `GET /etablissements/{id}/console/notes` | UC60/61 | `?classe_id=&annee_academique=&periode=&limit=&offset=` (moyennes/bulletins) |
| 13 | `POST /etablissements/{id}/postes` *(existant, payload étendu)* | UC62 | `+ description, matiere, remuneration_min, remuneration_max?, schema_formulaire?` |
| 14 | `POST /postes/{id}/candidatures` *(existant, payload étendu)* | UC63 | `+ reponses_formulaire?` (JSON, validé contre `schema_formulaire` du poste) |
| 15 | `POST /etablissements/{id}/types-actes` *(existant, payload étendu)* | UC64 | `+ schema_formulaire?` |
| 16 | `POST /demandes-actes` *(existant, payload étendu)* | UC65 | `+ reponses_formulaire?` |
| 17 | `POST /demandes-actes/{id}/livrer-document` | UC66 | Multipart, upload LuluFiles, réservé A+/A++, exige `statut=acceptee` |
| 18 | `GET /demandes-actes/{id}/lien-document` | UC67 | Réservé au titulaire/tuteur, exige `document_final_lulufiles_id` renseigné |
| 19 | `GET /tickets-transport/{id}/pdf`, `GET /tickets-cantine/{id}/pdf`, `GET /billets/{id}/pdf` | UC68 | PDF+QR, réservé au propriétaire du ticket |
| 20 | `POST /valider-acces` *(existant, inchangé)* | UC69 | Aucun changement serveur — le frontend ajoute un mode scan qui appelle le même endpoint avec l'id décodé du QR |
| 21 | *(pas de nouvel endpoint)* | UC70 | Réutilise `POST /etablissements/{id}/controleurs` et `POST /evenements/{id}/parrain` déjà existants — unification d'écran seulement |

Micro-jobs/marketplace (UC-57/58 du cahier des charges) : changement de **RBAC uniquement** sur des endpoints déjà existants (`accepter_offre` restreint à Étudiant, `_ROLES_CLIENT`/`_ROLES_PRESTATAIRE` révisés dans `micro_jobs/router.py` ; garde marketplace basculée d'un critère d'âge à la dérivation étudiant) — aucune nouvelle route.

Aucun point technique non tranché ne bloque le passage au backend.
