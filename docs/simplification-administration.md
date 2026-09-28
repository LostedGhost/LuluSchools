# Simplification du travail des administrateurs (A+ et A++)

2026-09-28. Principe : ce qui peut être automatisé l'est ; ce qui peut être groupé l'est ;
l'IA **prépare** le reste, l'administrateur **décide**. Aucune décision ayant un effet
significatif sur une personne n'est prise par la machine seule (Art. 401 de la loi
n° 2017-20) ; les données pénales (casiers judiciaires) ne sont jamais transmises à l'IA
(Art. 395).

## Boîte « À traiter »

Première entrée du menu de l'A+ et de l'A++ (`GET /administration/a-traiter`). Toutes les
files d'attente de la plateforme en une page, urgentes en tête, avec les actions groupées
et ce que l'IA a préparé. Une section n'apparaît que si elle contient quelque chose.

## Ce qui a changé, file par file

| File | Avant | Maintenant |
|---|---|---|
| Inscriptions | Validation une par une | **Validation en lot** (ordre d'arrivée, dans la limite des places) et rejet en lot avec motif commun ; **admission automatique** optionnelle [Délégué] pour les classes à l'ordre d'arrivée (jamais de refus automatique, ni pour un concours ou un tirage au sort) |
| Actes | L'A+ acceptait puis téléversait chaque document | **Attestation de scolarité et relevé de notes générés et livrés automatiquement** dès le paiement (données réelles : inscription, copies corrigées, bulletin) ; en cas d'échec, relance en un clic |
| Réclamations de note | Lecture de la copie par l'A+ | **Avis de l'IA** joint (copie, barème, points, motif), l'A+ tranche |
| Recrutement | Notation manuelle dès un échec de l'IA ; contrat rédigé à la main | **Renotation automatique** (toutes les heures, 3 essais) ; **« Recruter » en un clic** : contrat pré-rempli, syllabus rédigé par l'IA, échéance au 30 juin. Le verdict sur le casier reste entièrement humain |
| Reconductions | Une proposition par contrat | **Tout reconduire** en un clic (contrats dans la fenêtre de 30 jours) |
| Affectations | Enseignant par enseignant, classe par classe | **Proposition calculée** (matières non couvertes, professeurs principaux manquants, charge équilibrée), appliquée en un clic après relecture |
| Signalements (messages, annonces) | Lecture de chaque signalement | **Triage par l'IA** (gravité, résumé, décision suggérée) et **application en lot** des suggestions ; « à examiner » n'est jamais appliqué en lot |
| Litiges (marketplace, micro-jobs) | Examen sans aide | **Avis de l'IA** motivé ; décision en un clic |
| Remboursements | Statut « remboursé » sans remboursement réel | **Remboursement Kkiapay automatique** (API `transactions/revert`) pour les tickets, billets, ventes et missions ; un échec apparaît dans « Remboursements à faire à la main » |
| Reversements aux vendeurs et prestataires | Une référence par vente/mission | **Regroupés par bénéficiaire** : un seul virement Mobile Money, une seule référence |

Kkiapay ne permet pas de virer de l'argent vers un tiers (son « payout » ne reverse que le
solde du marchand vers son propre compte ; vérifié dans le SDK officiel) : les reversements
restent donc un virement humain, simplement regroupé.

## Migration

`0019_simplification_admin` : colonnes des automatisations et des avis de l'IA ; les
remboursements antérieurs sont marqués comme effectués (ils avaient été traités à la main).
