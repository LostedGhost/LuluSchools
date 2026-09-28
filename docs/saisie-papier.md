# Saisie papier (« guichet papier »)

2026-09-28. Pour les personnes **sans smartphone** — enseignants sans téléphone Android,
élèves, parents — l'administration de l'établissement (A+) enregistre leurs documents
papier à partir d'une simple photo.

## Principe, identique partout [Délégué]

1. **Photographier** : téléphone ou tablette (appareil photo), ou fichier/PDF de scanner ;
   **plusieurs pages par document** (8 au maximum, sélection multiple ou photos successives ;
   40 pour les copies d'un devoir). La
   photo est **conservée comme preuve** (LuluFiles) dans le registre `documents_papier`.
2. **Lire** : FreeLLM (vision) propose une lecture ; les noms lus sont rapprochés des élèves
   de la classe (accents, ordre nom/prénom, fautes légères), avec un niveau de confiance
   « reconnu / à vérifier / non reconnu ».
3. **Vérifier et valider** : l'administrateur relit et corrige chaque valeur à l'écran, la
   photo sous les yeux, puis confirme. **L'IA ne décide rien** (Art. 401). Si l'IA échoue, la
   même grille se remplit à la main.
4. **Tracer** : qui a saisi, quand, ce que l'IA avait lu, ce qui a été enregistré et l'objet
   créé. Historique et photos consultables en bas de la page *Saisie papier* ; une saisie lue
   mais jamais validée remonte dans « À traiter » (« Saisies papier à terminer »).

Vérifié avec le vrai FreeLLM sur une feuille manuscrite simulée : 8/8 lignes (notes décimales,
« Abs ») lues en ~25 s ; parcours complet en navigateur (lecture ~40 s, 5/5 élèves reconnus).

## Ce qui peut être saisi

| Pour qui | Document papier | Résultat sur la plateforme | Où |
|---|---|---|---|
| Enseignant | **Feuille de notes** | Une évaluation « sur papier » de l'enseignant (matière, date, barème de la feuille) et une note par élève ; comptée dans les bulletins. Un élève absent compte 0 (règle UC-08). | A+ › Saisie papier |
| Enseignant | **Feuille d'appel** | Absences et retards dans la vie scolaire (mention « feuille d'appel papier », sans doublon le même jour) | A+ › Saisie papier |
| Enseignant | **Cours écrit** | Cours texte (transcription Markdown relue) publié au nom de l'enseignant ; El Professor et les quiz s'appuient dessus | A+ › Saisie papier |
| Enseignant | **Contrat signé à la main** | Contrat « signé » : on imprime le PDF du contrat, l'enseignant signe, on photographie. Le PDF du contrat mentionne la signature papier et qui l'a enregistrée. | A+ › Recrutement › « Signé sur papier » |
| Élève | **Copies d'un devoir** | Une photo par copie ; l'IA lit le nom écrit sur la copie et propose l'élève ; après confirmation, la copie est corrigée par l'IA selon le barème (comme une copie photographiée par l'élève). Autorisé après la date limite : la copie a été rendue à temps sur papier. | A+ › Saisie papier, et l'enseignant du devoir (Mes devoirs › « Copies papier ») |
| Parent | **Fiche d'inscription** | Élève créé (sans compte parent), inscrit et admis dans la limite des places ; **fiche d'identifiants imprimable** (matricule, mot de passe provisoire) remise à la famille. Moins de 16 ans : la fiche doit porter la signature du parent (consentement, Art. 446). | A+ › Saisie papier |
| Parent | **Consentement parental signé** | L'inscription en attente de consentement passe « soumise » (consentement horodaté, photo du formulaire conservée comme preuve, Art. 389-390) ; admission automatique si activée | A+ › Saisie papier |

## Technique

- Backend : `app/modules/saisie_papier/` (`models.py` registre, `lecture.py` consignes /
  préparation des photos / rapprochement des noms, `router.py`) ; `FreeLLMClient.lire_document_papier`
  (délai 240 s) ; migration `0020_saisie_papier` (idempotente) ;
  `valider_inscription_interne` renvoie désormais le mot de passe provisoire.
- Frontend : `pages/admin_etablissement/SaisiePapierPage.tsx` (menu A+ « Saisie papier »),
  `components/saisie_papier/PrisePhotos.tsx` (appareil photo / fichiers, aperçus) et
  `CopiesPapier.tsx`, `api/saisie_papier.ts`.
- Tests : `tests/test_saisie_papier.py` (IA simulée, dont l'échec de lecture et la saisie manuelle).

## Limites connues

- Une copie = une photo (la page avec le nom) ; une copie de plusieurs pages se corrige sur sa
  première page, comme une copie photographiée par l'élève.
- La fiche d'inscription au guichet crée l'élève sans compte parent : si le parent crée plus
  tard un compte, le rattachement à l'enfant n'est pas encore automatique.
- Le paiement d'un acte au guichet (espèces) n'est pas couvert : les actes restent payés via
  Kkiapay.
