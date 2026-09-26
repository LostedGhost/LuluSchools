# LuluSchools — Cas d'utilisation, Phase 4 (Marketplace étudiante)

Rédigé selon la méthode `lucio-dev` (pipeline spec-first), même format que `docs/cas-utilisation-phase-1.md` et `docs/cas-utilisation-phase-2-3.md`. **Brouillon — pas encore validé.** Trois points structurants ont été tranchés explicitement par l'utilisateur (2026-09-26, via AskUserQuestion) avant même ce premier jet ; le reste des règles métier ci-dessous applique la délégation déjà accordée sur ce projet ([[feedback-legal-autonomy]]) et est marqué **[Délégué]**, à relire et corriger avant validation finale.

Cadrage : nouvelle fonctionnalité, absente du périmètre initial Phase 1/2/3 (voir `SUIVI-PROJET.md`) — traitée comme une Phase 4 indépendante, sans dépendance technique sur les Phases 2/3 hormis la réutilisation du modèle de séquestre Kkiapay déjà validé (UC-18, ADR-008) et du stockage de photos via LuluFiles (ADR-003/ADR-009).

**Cadre juridique (Livre IV, commerce électronique, loi n° 2017-20)** : l'Art. 326 al. 4 limite l'application des dispositions protectrices du consommateur (information précontractuelle Art. 338-342, droit de rétractation Art. 347-356, garanties légales Art. 357-376) aux contrats conclus **entre un professionnel et un consommateur**. Un élève qui revend un article personnel n'est pas un professionnel — cette marketplace est donc une transaction **entre particuliers (C2C)**, hors du régime consumériste lourd de ce Livre. Restent applicables quel que soit le statut des parties : l'obligation générale de vigilance de LuluSchools en tant qu'opérateur de la plateforme (Art. 377, sans obligation de surveillance générale préalable — Art. 499) et l'obligation de disposer d'un dispositif de signalement accessible (Art. 500, pris par analogie — cet article vise nommément l'apologie de crimes/pornographie enfantine, mais le mécanisme de signalement déjà en place pour la messagerie, UC-13, est repris ici par cohérence de plateforme plutôt que comme obligation stricte). **Zone d'ambiguïté signalée plutôt que tranchée** : l'Art. 328 (obligation générale d'information/identité) vise "toute personne exerçant une activité de commerce électronique", formulation plus large que "professionnel" — une vente ponctuelle d'un objet personnel par un élève ne constitue vraisemblablement pas l'exercice habituel d'une "activité", mais ce n'est pas expressément défini dans la loi ; à confirmer si le volume de reventes explose au point de ressembler à une activité commerciale déguisée.

## Acteurs

Élève (vendeur et/ou acheteur, seul rôle autorisé — décision explicite) · A+ (modération : retrait d'annonce, arbitrage de litige) · A++ (lecture seule, cohérent avec le reste de la plateforme).

---

## UC-20 — Publier et consulter une annonce marketplace

> En tant qu'élève de mon établissement, je veux publier une annonce pour vendre un article personnel, afin de le proposer aux autres élèves de mon établissement.

- **Réservé aux élèves ≥16 ans (décision explicite)** : un élève <16 ans ne peut ni publier ni acheter sur la marketplace, sans exception ni palier de consentement tuteur (contrairement à l'inscription, UC-01/02, ou aux sessions live, UC-16). Vérifié contre la date de naissance déjà enregistrée à l'inscription.
- **Restreint à l'établissement de l'élève (décision explicite)** : une annonce n'est visible et achetable que par les élèves inscrits dans le même établissement que le vendeur (même périmètre RBAC que la messagerie de classe) — pas de marketplace inter-établissements ni nationale en V1.
- Champs de l'annonce : titre, description, catégorie (liste fermée ci-dessous), état de l'article (`neuf` / `très bon état` / `bon état` / `usé`), prix (entier, strictement positif — un prix à 0 n'est pas modélisé ici, le don est une fonctionnalité différente), au moins une photo **[Délégué]** — stockage via LuluFiles, lien signé résolu à la demande (même pattern qu'ADR-009), jamais en masse.
- **Catégories fermées en V1 [Délégué]** : Fournitures scolaires, Manuels/livres, Vêtements & uniformes, Électronique, Autre. Sont explicitement exclus de la plateforme, quelle que soit la catégorie choisie : armes, alcool/tabac, produits stupéfiants ou pharmaceutiques, contenu à caractère sexuel, contrefaçons — exclusion justifiée par la protection des mineurs et l'ordre public (Art. 327) plutôt que laissée à l'appréciation de chaque élève.
- Une annonce = un article unique, pas de gestion de stock/quantité **[Délégué]** — cohérent avec l'esprit "vente d'objets personnels entre élèves" plutôt qu'un vrai commerce de volume ; une évolution future indépendante si le besoin apparaît.
- Cycle de vie d'une annonce : `disponible` → `réservée` (dès qu'un acheteur amorce un paiement, voir UC-21) → `vendue` (séquestre libéré) ou de retour à `disponible` (paiement non finalisé, litige tranché en faveur de l'acheteur avec remboursement) → `retirée` (par le vendeur avant toute réservation, ou par l'A+ en modération).
- Un seul acheteur à la fois par annonce **[Délégué]** — pas de système d'enchères ni de file d'attente de plusieurs acheteurs intéressés simultanément.
- **Signalement et modération [Délégué]** : chaque annonce affiche un bouton "signaler" visible par tout élève de l'établissement (même mécanique que la messagerie, UC-13) ; un signalement notifie l'A+ de l'établissement, qui peut retirer l'annonce (statut `retirée`, motif conservé) sans devoir attendre un signalement pour agir de sa propre initiative.

## UC-21 — Réserver et acheter un article avec séquestre

> En tant qu'élève acheteur, je veux payer un article réservé de façon sécurisée, afin d'être protégé si l'article reçu ne correspond pas à l'annonce.

- **Séquestre Kkiapay, même mécanique qu'UC-18 (ADR-008)** : paiement amorcé par l'acheteur (`POST .../paiement/amorcer` + webhook), montant retenu jusqu'à confirmation de réception ; reversement au vendeur fait manuellement par un opérateur en V1 (même limite déjà documentée : `setup_payout` Kkiapay ne permet pas un virement ponctuel fiable vers un tiers).
- **Remise en main propre uniquement [Délégué]** — cohérent avec le périmètre restreint au même établissement (UC-20) : pas de livraison/transporteur à modéliser en V1.
- Une fois le paiement amorcé, l'annonce passe `réservée` et n'est plus achetable par un autre élève tant que la transaction n'est pas résolue (paiement échoué → retour à `disponible`).
- **Confirmation de réception** : le vendeur marque la remise comme effectuée (`remis`) après l'avoir faite en personne ; l'acheteur dispose alors de 5 jours ouvrés pour confirmer la conformité (séquestre libéré, annonce `vendue`) ou contester (voir UC-22) — délai identique à UC-04b/UC-18 pour rester cohérent sur toute la plateforme. Passé ce délai sans réaction, la réception est considérée tacitement conforme et le séquestre est libéré.
- **Pas de commission de plateforme en V1 [Délégué]** — cohérent avec UC-18, le vendeur reçoit l'intégralité du prix convenu.
- Comme il s'agit d'une transaction entre particuliers (Art. 326 al. 4, voir cadrage plus haut), aucun délai légal de rétractation n'est dû à l'acheteur au sens du Livre IV ; la fenêtre de 5 jours ci-dessus est une protection produit, pas une obligation légale de ce Livre.

## UC-22 — Litige de réception

> En tant qu'élève acheteur, je veux contester la conformité d'un article reçu, afin d'obtenir un remboursement si l'article ne correspond pas à l'annonce.

- Contestation possible uniquement dans la fenêtre de 5 jours ouvrés après que le vendeur a marqué la remise comme effectuée (voir UC-21) — au-delà, la réception est tacitement validée.
- **Arbitrage par l'A+ de l'établissement [Délégué]** — sans l'ambiguïté rencontrée sur UC-18 (où prestataire et client peuvent appartenir à des établissements différents) : ici vendeur et acheteur sont toujours du même établissement (UC-20), l'A+ compétent est donc non ambigu.
- Décision de l'A+ : accepté (séquestre remboursé à l'acheteur, annonce repasse `disponible`) ou rejeté (séquestre libéré au vendeur) — motif et horodatage conservés, même format que les autres mécanismes de contestation de la plateforme (UC-04b, UC-18).
- Pas de médiation à trois ni d'expertise technique de l'article en V1 **[Délégué]** — l'A+ tranche sur pièces (description de l'annonce, échange de messages éventuel, déclarations des deux parties), pas de processus d'expertise formalisé pour un objet de faible valeur.

---

## État de validation — Phase 4 (2026-09-26)

**Tranché explicitement par l'utilisateur (avant rédaction, via AskUserQuestion) :**
1. Modèle de transaction : paiement intégré avec séquestre Kkiapay (pas une simple vitrine d'annonces, pas de paiement direct sans séquestre).
2. Participants : élèves de l'établissement uniquement (ni tuteurs, ni enseignants, ni marketplace nationale).
3. Mineurs : marketplace réservée aux élèves ≥16 ans, aucun palier de consentement tuteur en dessous (contrairement à l'inscription).

**Décisions produit déléguées (marquées `[Délégué]` ci-dessus)** : champs et photo obligatoire d'une annonce, liste fermée de catégories + exclusions (armes/alcool/tabac/stupéfiants/contrefaçon/contenu sexuel), pas de gestion de quantité/stock, un seul acheteur à la fois, signalement + modération A+, remise en main propre uniquement, délai de confirmation/contestation de 5 jours (calqué sur UC-04b/UC-18), pas de commission de plateforme, arbitrage par l'A+ de l'établissement, pas de médiation/expertise formalisée.

**Point de vigilance signalé, non bloquant pour la suite du pipeline** : la capacité civile d'un mineur de 16-17 ans à conclure seul un contrat de vente (Code civil béninois, hors périmètre de la loi n° 2017-20) n'a pas de réponse déjà verrouillée sur ce projet — le seuil ≥16 ans retenu s'aligne sur celui déjà utilisé pour l'auto-validation d'inscription (Art. 446), mais mériterait une confirmation juridique complémentaire avant un déploiement à grande échelle, dans le même esprit que les points 🔓 déjà identifiés sur UC-18 (âge minimum micro-job) et UC-19 (autorisation de vol de drone).

**Prochaine étape** : validation explicite de ce document par l'utilisateur (champs, catégories, délais) avant de passer à l'étape 2 du pipeline (diagrammes UML dérivés de ces UC).
