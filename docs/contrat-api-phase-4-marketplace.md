# LuluSchools — Contrat d'API, Phase 4 (Marketplace étudiante)

Dérivé strictement de `docs/cas-utilisation-phase-4-marketplace.md` (validé) et `docs/diagrammes-uml-phase-4-marketplace.md` (validé), étape 3 de la méthode `lucio-dev`. **Choix technique explicitement non repris ici, sur demande de l'utilisateur** : la stack ne change pas (FastAPI/PostgreSQL/React, monolithe modulaire, Kkiapay, LuluFiles — voir `docs/choix-technique-phase1.md`, ADR-001/002/003), et aucune nouvelle intégration externe n'est nécessaire — le séquestre et le stockage photo réutilisent des mécanismes déjà validés (ADR-008, ADR-003/009). Mêmes conventions que `docs/contrat-api-phase1.md` (base `/api/v1`, JWT Bearer, pagination `?page=&page_size=`, enveloppe d'erreur `{"error": {...}}`, upload multipart + lien signé pour les fichiers) — non dupliquées ici.

**Séquestre (UC-21)** : même modèle "Option A" qu'UC-18 (`docs/adr/ADR-008-kkiapay-pas-de-versement-tiers.md`) — le séquestre est un statut suivi par LuluSchools, pas un mécanisme Kkiapay natif ; le reversement au vendeur est déclenché manuellement par un opérateur humain en V1 (voir `reverser-vendeur` ci-dessous). Pas besoin de revérifier le SDK Kkiapay pour cette phase : la limite (`setup_payout` ne permet pas un virement ponctuel fiable vers un tiers) a déjà été établie pour UC-18 et s'applique à l'identique ici.

## Annonces (UC-20)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/etablissements/{id}/marketplace/annonces` | Élève ≥16 ans de cet établissement | Multipart : `titre`, `description`, `categorie` (`fournitures_scolaires`\|`manuels_livres`\|`vetements_uniformes`\|`electronique`\|`autre`), `etat` (`neuf`\|`tres_bon_etat`\|`bon_etat`\|`use`), `prix` (int, strictement positif) + 1..n fichiers image. Refusé (`422`) si aucune photo jointe (au moins une obligatoire, UC-20 délégué). Statut initial `disponible` |
| GET | `/etablissements/{id}/marketplace/annonces` | Élève ≥16 ans de cet établissement | Catalogue, filtres optionnels `?categorie=&etat=&prix_min=&prix_max=`, pagination standard, statut `disponible` par défaut (`?statut=` pour élargir) |
| GET | `/marketplace/annonces/{id}` | Élève ≥16 ans du même établissement que l'annonce | Lecture, photos résolues en liens signés LuluFiles à la demande (ADR-009), jamais en masse |
| DELETE | `/marketplace/annonces/{id}` | vendeur propriétaire | Autorisé seulement si `disponible` (`409` sinon, ex. déjà réservée) → `retirée` |
| POST | `/marketplace/annonces/{id}/retirer` | A+ de l'établissement de l'annonce | Modération, `motif` obligatoire, possible à tout statut sauf `vendue`. Si `réservée`, rembourse automatiquement la transaction en cours (voir `remboursee` ci-dessous) avant de passer l'annonce à `retirée` |
| POST | `/marketplace/annonces/{id}/signaler` | élève du même établissement que l'annonce | Visible par l'A+ via l'endpoint ci-dessous, même logique que la messagerie (UC-13) |
| GET | `/etablissements/{id}/marketplace/signalements` | A+ | Signalements non traités pour les annonces de son établissement |
| POST | `/marketplace/signalements/{id}/traiter` | A+ | Marque traité, `decision` en texte libre conservée |
| GET | `/mes-annonces-marketplace` | Élève | Historique de mes annonces publiées (tous statuts) |

## Achat avec séquestre et litige (UC-21, UC-22)

| Méthode | Chemin | Rôle | Notes |
|---|---|---|---|
| POST | `/marketplace/annonces/{id}/reserver` | Élève acheteur (≠ vendeur, même établissement) | Refusé (`409`) si l'annonce n'est pas `disponible`. Crée la `TransactionMarketplace` (statut initial `en_attente_paiement`), annonce → `réservée` |
| POST | `/marketplace/transactions/{id}/paiement/amorcer` | acheteur propriétaire de la transaction | Même mécanique `paiement/amorcer` que UC-10/UC-11/UC-17/UC-18 : le compte Kkiapay unique de LuluSchools encaisse le prix. Webhook confirmé → `en_attente_paiement` → `paiement_confirme` (même granularité que le statut `ouverte` des offres micro-job après webhook, UC-18) |
| POST | `/marketplace/transactions/{id}/annuler` | acheteur propriétaire | Uniquement tant que `en_attente_paiement` (paiement pas encore confirmé) → `annulee`, annonce repasse `disponible` **[Délégué, complétude technique — même pattern que l'annulation d'une offre micro-job avant paiement, UC-18]** |
| POST | `/marketplace/transactions/{id}/declarer-remise` | vendeur (propriétaire de l'annonce liée) | Refusé (`409`) si statut ≠ `paiement_confirme`. → `remise_declaree`, fixe `date_limite_confirmation` = +5 jours ouvrés (délégué UC-21, cohérent avec UC-04b/UC-18) |
| POST | `/marketplace/transactions/{id}/confirmer` | acheteur propriétaire | `remise_declaree` → `confirmee` (validation explicite de la conformité). Passé `date_limite_confirmation` sans action, un job périodique (ou calcul à la volée en lecture, comme UC-11/UC-18) considère la transaction `confirmee` tacitement |
| POST | `/marketplace/transactions/{id}/contester` | acheteur propriétaire | Uniquement avant `date_limite_confirmation`, `remise_declaree` → `contestee` |
| POST | `/marketplace/contestations/{id}/decision` | A+ de l'établissement concerné | `acceptee` (transaction → `remboursee` — remboursement de l'acheteur, même capacité Kkiapay déjà utilisée pour les remboursements de tickets/billets, pas un nouveau reversement tiers — annonce repasse `disponible`) ou `rejetee` (`motif` obligatoire, transaction → `confirmee`, poursuit vers le reversement) — même schéma que UC-04b/UC-18, arbitrage non ambigu ici car vendeur et acheteur sont toujours du même établissement (voir UC-22) |
| POST | `/marketplace/transactions/{id}/reverser-vendeur` | A+ de l'établissement | Autorisé seulement si statut `confirmee`. Reversement manuel hors Kkiapay (mobile money direct vers le vendeur, Option A ADR-008) ; `reference_paiement` (texte libre, preuve) obligatoire pour passer `confirmee` → `finalisee`. Annonce → `vendue` |
| GET | `/mes-transactions-marketplace` | Élève | Historique, comme acheteur et comme vendeur |

---

## Points laissés à l'implémentation (étape 4), sans impact sur ce contrat

- Job de passage `paiement_confirme`/`remise_declaree` → `confirmee` tacite après `date_limite_confirmation` : calcul à la volée en lecture vs tâche planifiée, même remarque que UC-11/UC-12/UC-17/UC-18 — n'affecte pas le contrat observable.
- Le remboursement de l'acheteur d'origine (`contestation acceptee` → `remboursee`) réutilise la même capacité Kkiapay déjà exploitée pour les remboursements de tickets/billets (Phase 2/3), aucune vérification SDK supplémentaire nécessaire — seul le reversement vers un tiers (`reverser-vendeur`) reste manuel (limite déjà établie, ADR-008).
