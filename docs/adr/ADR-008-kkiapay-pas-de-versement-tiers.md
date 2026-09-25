# ADR-008 : Kkiapay ne supporte pas de versement programmable à un tiers — impact sur le séquestre des micro-jobs (UC-18)

## Statut
**Proposé, en attente de décision de l'utilisateur** (voir la question posée en conversation) — remet en cause un principe jusqu'ici verrouillé pour tout le projet ("LuluSchools n'héberge jamais les fonds elle-même"), donc traité comme un point structurant à valider explicitement plutôt que délégué silencieusement, contrairement aux autres points techniques de l'étape 3.

## Contexte
UC-18 (`docs/cas-utilisation-phase-2-3.md`) prévoit un séquestre : le client paie via Kkiapay, le paiement est retenu, et le prestataire n'est payé qu'après validation de la mission. Ce mécanisme suppose que la plateforme (ou Kkiapay) puisse **reverser une somme à un tiers** (le prestataire) distinct de celui qui a réglé la facture Kkiapay de LuluSchools.

Vérification faite sur la documentation officielle Kkiapay (`docs.kkiapay.me`) avant d'écrire le contrat d'API :
- Kkiapay est un système de **règlement marchand classique**, pas une plateforme de versement/marketplace. Un compte Kkiapay ne peut demander le retrait ("reversement") que de **son propre solde** vers **son propre compte** bancaire ou mobile money déjà configuré dans son tableau de bord — jamais vers un tiers.
- Les fonds collectés transitent par un "solde d'opération" puis un "solde de disponibilité" (même jour pour mobile money, 72h pour carte) avant d'être retirables, mais toujours vers le même titulaire de compte marchand.
- Aucun endpoint API de type "payout"/"transfer vers un bénéficiaire" n'existe dans leur documentation publique — le retrait est une opération manuelle depuis le tableau de bord.

**Conséquence concrète** : le compte Kkiapay de LuluSchools (un seul compte pour toute la plateforme, cohérent avec UC-10/UC-11/UC-12/UC-17) peut collecter le paiement du client d'un micro-job, mais **ne peut pas** reverser automatiquement la part du prestataire par API. Ce n'est pas un point d'intégration technique mineur : ça touche directement au principe déjà verrouillé pour tout le reste du projet, "LuluSchools n'héberge jamais les fonds elle-même" — pour cette UC précise, si le séquestre passe par le compte Kkiapay de LuluSchools, LuluSchools *héberge* de fait la somme du client jusqu'à ce qu'un humain la reverse manuellement au prestataire.

## Options identifiées (aucune tranchée ici)

**Option A — Séquestre réel via le compte Kkiapay de LuluSchools, reversement manuel.** Le client paie sur le compte Kkiapay de la plateforme comme pour les autres UC (tickets, actes, billets). À la validation de la mission, un opérateur humain (A+ ou équipe LuluSchools) déclenche un transfert mobile money manuel vers le prestataire, hors Kkiapay, et enregistre une preuve de paiement dans l'app (comme une pièce jointe). Le "séquestre" devient un statut suivi par le logiciel, pas une opération financière automatisée. Réintroduit exactement le risque que le principe "jamais héberger les fonds" cherchait à éviter, uniquement pour cette fonctionnalité.

**Option B — Pas de flux d'argent réel dans l'app, mise en relation seulement.** LuluSchools héberge l'offre, l'acceptation, la déclaration de fin et la validation/contestation (tout le workflow UC-18 sauf le paiement), mais le règlement du prestataire se fait **en dehors de la plateforme**, directement entre client et prestataire (mobile money personnel, espèces). Préserve intégralement le principe déjà verrouillé, mais la fonctionnalité n'est plus vraiment "sécurisée par séquestre" comme le nom de l'UC le suggère — c'est un tableau d'annonces avec suivi de litige, pas un paiement sécurisé.

**Option C — Reporter UC-18 hors de ce lot de travail.** Traiter le séquestre comme un sujet d'architecture à part entière (évaluer un second agrégateur de paiement qui supporte nativement le versement à un tiers, ou négocier une fonctionnalité marketplace directement avec Kkiapay) avant d'écrire le contrat d'API de cette UC précise ; les 18 autres UC (Phase 2 + reste de la Phase 3) avancent sans attendre.

## Pourquoi ce n'est pas délégué comme les autres points techniques de l'étape 3
Les deux autres points techniques reportés à l'étape 3 (infra live, hébergement vidéo) sont des choix de fournisseur sans impact sur un principe déjà acté avec l'utilisateur. Celui-ci rouvre directement une décision structurante déjà verrouillée project-wide ("LuluSchools n'héberge jamais les fonds elle-même") et a une implication financière/réglementaire potentielle (une somme détenue pour le compte d'un tiers avant reversement peut relever d'un régime différent de la simple perception d'une redevance de service, question hors du périmètre de la loi n° 2017-20 et du skill `droit-numerique-benin` — plutôt de la réglementation des systèmes de paiement UEMOA/BCEAO) — exactement le type de point que la délégation de l'utilisateur exclut explicitement (voir [[feedback-legal-autonomy]]).
