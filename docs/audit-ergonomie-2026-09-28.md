# Audit d'ergonomie — 2026-09-28

Passe complète sur les 79 pages, pour les cinq rôles, sur ordinateur et au format téléphone
(375 px). Méthode : lecture du code, script d'audit automatisé exécuté dans le navigateur
(`frontend/scripts/audit_ergonomie.js`) sur chaque page de chaque rôle, puis vérification à
l'écran des corrections.

## Ce qui a été trouvé et corrigé

### Bloquant sur téléphone
- **Menu inaccessible** : la barre du bas n'affichait que les 5 premières entrées, sans autre
  menu. Un A+ ne pouvait pas atteindre 12 de ses 17 écrans, un enseignant 7 sur 12, et
  **personne ne pouvait se déconnecter sur téléphone**. La 5e entrée est désormais « Plus »,
  qui ouvre le menu complet (toutes les entrées, profil, thème, déconnexion).
- **Contenu décalé de 68 px** sur toutes les pages connectées (règle CSS de la barre latérale
  repliée appliquée alors que la barre est masquée) : un quart de l'écran perdu.
- Débordements horizontaux (recrutement, marketplace A+, alertes El Professor, bulletin).

### Fonctionnel
- **Bulletin** : les onglets « Trimestre 1/2/3 » affichaient tous la même moyenne (le calcul
  ignorait la période), et une université se voyait proposer des trimestres. [Délégué]
  Découpage retenu (`backend/app/modules/evaluations/periodes.py`) : trimestres
  1er sept.–31 déc. / 1er janv.–31 mars / 1er avril–31 août pour le primaire et le
  secondaire ; semestres 1er sept.–31 janv. / 1er fév.–31 août pour l'université. Un devoir
  compte dans la période qui contient sa date limite. `GET /classes/{id}/periodes` donne les
  périodes et celle en cours ; le bulletin s'ouvre sur la période en cours.
- **Tableau de bord élève** : série de 12 jours, niveau 4 / 680 XP, médailles et « quêtes »
  étaient des valeurs fictives codées en dur, « EP01 » s'affichait même à un étudiant de
  l'UAC et l'encart bulletin était figé à « —/20 ». Remplacé par des données réelles :
  devoirs à rendre (avec échéance), moyenne de la période en cours, badges du passeport.
- Note des documents de candidature affichée « /10 » côté enseignant alors qu'elle est sur 100.

### Messages et libellés
- **330 messages du serveur** réaccentués (erreurs, e-mails, notifications, PDF) ; les
  messages qui citaient des routes ou des noms de champs (« POST /auth/change-password »,
  « eleve_utilisateur_id est requis ») sont réécrits pour l'utilisateur.
- **Erreurs de validation (422)** traduites en phrases (« Le champ « prénom » est
  obligatoire. ») au lieu de « Données invalides » (`app/core/messages_validation.py`).
- **Aucune valeur technique à l'écran** : `frontend/src/utils/libelles.ts` donne le libellé
  de chaque statut, rôle, type ou période (« en_attente » → « En attente »). Côté serveur,
  la boîte « À traiter » libelle aussi l'origine des alertes et le type des documents.
- Données de démonstration (seed) accentuées : prénoms, événements, offres, motifs.

### Retours d'action et confirmations
- **Confirmation avant toute action lourde ou irréversible** (`useConfirmation()`,
  `components/Modale.tsx`) : validations et rejets en lot, reconductions, application des
  suggestions de l'IA, litiges, virements, remboursements, annulations, suppressions, verdict
  sur casier, effacement du tableau, suppression d'une conversation El Professor.
- Les panneaux d'action de l'A++ (suspension, masquage, annulation, arbitrage, reversement)
  s'ouvraient sous le tableau, hors de vue : ce sont maintenant des fenêtres de dialogue.
- **Succès** : notification flottante en bas de l'écran, qui disparaît seule (avant, le
  message restait affiché en haut de page, souvent hors de vue).
- **Erreur** : le bandeau défile jusqu'à être visible.

### Pastilles et accueil
- **Pastilles de menu** (`GET /me/compteurs`) : total « À traiter » (A+, A++), consentements
  et dépenses à valider (parent), contrats à signer et copies à reprendre (enseignant),
  devoirs à rendre (élève). Rafraîchies à chaque changement de page et toutes les 2 minutes.
- **Guide de première connexion** par rôle (`components/GuideDemarrage.tsx`) : les quatre
  premières choses à faire, fermable, en tête du tableau de bord.

### Accessibilité
- `Field` relie l'étiquette au champ (`htmlFor`, `aria-describedby`, `aria-invalid`), y
  compris quand le champ est accompagné d'un bouton (mot de passe).
- Champs et filtres sans étiquette visible : nom accessible (texte indicatif, option
  « Tous… »), recherche des tableaux étiquetée.
- Cibles tactiles d'au moins 40 px sur écran tactile ; lien imbriqué dans un bouton supprimé.
- **Contrastes (WCAG AA, 4,5:1)** : en thème sombre, le vert des liens et de l'entrée de menu
  active tombait à 2,9:1 et le rouge des erreurs à 3,5:1 ; en thème clair, le gris secondaire
  à 3,9:1. Couleurs ajustées (`index.css`) : pire cas désormais 4,67:1 (clair) et 4,89:1
  (sombre) pour tous les textes sur tous les fonds.
- Téléphone : un libellé de bouton long passe à la ligne au lieu de déborder.
- Fenêtres de dialogue : Échap, focus piégé puis restauré, `aria-modal`.
- Page des coefficients (A+) : 270 cartes à plat → filtrées sur les niveaux de
  l'établissement, recherche, regroupement par niveau.

## Conventions à respecter désormais
1. Jamais de valeur brute à l'écran : `libelle(valeur)`.
2. Toute action irréversible ou groupée passe par `useConfirmation()`.
3. Retour de succès : `SuccessBanner` (notification) ; erreur : `ErrorBanner` près de l'action.
4. Formulaires : `Field` autour du champ ; un filtre hors `Field` a un `aria-label`.
5. Messages du serveur : français accentué, sans jargon, avec ce qu'il faut faire.
6. Avant une livraison : `await (await import("/scripts/audit_ergonomie.js")).auditer([...])`
   dans le navigateur (serveur de dev), pour chaque rôle.
