# Documents officiels générés par la plateforme

2026-09-28. Tous les PDF partagent la même mise en page (`backend/app/core/pdf_officiel.py` :
en-tête aux couleurs de LuluSchools avec nom et code de l'établissement, titre, pied avec
référence de vérification). Les textes sont normalisés en Latin-1 (`latin1()`) : les polices
PDF de base n'ont ni tiret long, ni apostrophe typographique, ni « œ », qui s'affichaient « ? ».

| Document | Généré | Qui y accède | Où |
|---|---|---|---|
| Attestation de scolarité | Dès le paiement de la demande (ou tout de suite si gratuite) | Élève (document livré), A+ | Actes académiques |
| Relevé de notes | Idem | Idem | Actes académiques |
| **Certificat de réussite** | Dès qu'une décision **favorable** du conseil de classe existe : à la demande si elle existe déjà, sinon au moment où le conseil la prononce | Idem | Actes académiques (modèle « certificat de réussite » à choisir par l'A+) |
| **Bulletin de notes** (par période) | À la demande, calculé à l'instant | Élève, parent, enseignants de la classe, A+, A++ | Bulletin (élève), « Mes enfants » (parent), Conseil de classe (professeur principal) |
| **Contrat d'enseignement** | À la demande | Enseignant concerné, A+ de l'établissement, A++ | Mes contrats (enseignant), Recrutement (A+) |
| Passeport de compétences | À la demande | Élève, parent | Passeport |
| Tickets transport/cantine, billets | À l'achat | Acheteur | Services, Billetterie |

## Détails

- **Bulletin** (`GET /eleves/{id}/bulletins/pdf?classe_id=&periode=`) : identité, période et
  ses dates ; pour chaque matière, son coefficient, sa moyenne et le **détail de ses évaluations**
  (date, intitulé, note obtenue sur son barème, équivalent sur 100, « non rendu (0) » pour une
  copie manquante après l'échéance) ; moyenne générale pondérée et décision du conseil de classe
  (ou « en attente de délibération »). Pages de suite automatiques. Mêmes droits que la
  consultation du bulletin.
- **Contrat** (`GET /contrats/{id}/pdf`) : parties, poste, dates, syllabus complet (pages
  supplémentaires si besoin) et bloc de signature — image du tracé, horodatage, empreinte
  SHA-256 du syllabus signé, mention de signature électronique simple (art. 284-285). Avant
  signature, le même document marqué « En attente de signature » permet de le relire.
- **Certificat de réussite** : jamais sans délibération humaine (Art. 401). Sans décision
  favorable, la demande reste dans « À traiter » avec la mention « en attente d'une décision
  favorable du conseil de classe » ; l'A+ peut aussi la traiter à la main.

## Conseil de classe [Délégué]

Le professeur principal dispose d'un panneau « Conseil de classe » dans *Mes salles* : moyenne
de chaque élève pour la période, décision (Admis(e) en classe supérieure, Année validée,
Autorisé(e) à redoubler, Réorienté(e) — `backend/app/modules/evaluations/decisions.py`),
confirmation avant enregistrement (la décision fige le bulletin), bulletin PDF. Jusqu'ici,
aucune interface ne permettait d'enregistrer une décision de passage.

## Défaut corrigé au passage

Le titre des attestations et relevés de notes n'apparaissait pas (cadre trop petit de 0,3 pt :
PyMuPDF n'écrit rien quand le texte ne tient pas). Les actes déjà livrés avant ce correctif
n'ont pas de titre ; une nouvelle demande produit un document complet.
