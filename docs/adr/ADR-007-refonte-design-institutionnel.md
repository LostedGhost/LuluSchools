# ADR-007 : Refonte du design system vers une identité institutionnelle (État béninois), retrait du néo-brutalisme gamifié

## Statut
Accepté (remplace l'orientation visuelle décrite implicitement par le premier design system "Neo-Brutalism Gamifié × Claymorphism 3D" — décision explicite de l'utilisateur).

## Contexte
Le premier design system de LuluSchools (élaboré lors d'une itération précédente avec `/anthropic-skills:ui-ux-pro-max`) empruntait un langage visuel néo-brutaliste très marqué : ombres portées dures et non diffuses (`4px 4px 0 var(--border-strong)`), bordures épaisses (2 à 3px) sur quasiment tous les éléments, une palette à quatre accents décoratifs (vert, or/reward, rouge/action, violet/magic) utilisés de façon interchangeable, et de nombreux émojis utilisés comme icônes fonctionnelles (boutons, titres de page, badges, listes de statuts).

Ce langage convient à une application ludique ou à un produit grand public assumant un ton « jeu vidéo ». Il ne convient pas à une plateforme portée par l'État béninois pour piloter l'éducation nationale (inscriptions, actes académiques, recrutement des enseignants, bulletins, arbitrages ministériels) : le ton doit rester sobre, professionnel et digne de confiance, y compris quand certains éléments (XP, niveaux, séries de jours) restent utiles pour motiver les élèves.

L'utilisateur a demandé explicitement de revoir l'ensemble du frontend « dans le sens d'une plateforme de l'État béninois », en prenant `LuluFiles` (produit sœur du même porteur de projet) comme référence d'impression visuelle — sans en copier littéralement la charte — et en excluant strictement tout émoji de l'interface.

## Décision
- **Palette** : conservation des noms de variables CSS existants (`--primary`, `--reward`, `--action`, `--magic`, etc.) pour éviter de retoucher les ~40 fichiers qui les référencent, mais redéfinition de leurs valeurs et de leur usage :
  - `--primary` (vert) reste la couleur de marque et l'accent dominant.
  - `--reward` (ambre) et `--action` (rouge) sont recentrés sur un rôle strictement **fonctionnel** (récompense/attente vs. danger/erreur), plus jamais utilisés comme couleur de bouton décorative par défaut.
  - `--magic` (auparavant violet, décoratif) est aliasé sur les valeurs bleues de `--info` : le violet est retiré de la palette visible ; la variable est conservée pour ne rien casser silencieusement.
- **Ombres et bordures** : remplacement des ombres portées dures (`Npx Npx 0 couleur`) par des ombres diffuses et douces (`--shadow-sm/md/lg`, type `0 Npx Mpx rgba(...)`), et des bordures épaisses (2–3px, souvent `var(--border-strong)`) par des bordures fines (1–1.5px) ou leur suppression pure sur les blocs d'icônes teintés.
- **Typographie** : adoption de Rubik (300–900) comme police de titres et de corps, JetBrains Mono pour les données/identifiants, et Itim réservée exclusivement au wordmark « Lulu·Schools » (jamais en paragraphe ni en sous-titre) — aligné sur l'impression `LuluFiles`.
- **Émojis** : suppression totale de tout caractère émoji de l'interface (titres de page, boutons, badges, listes de statuts, décorations d'arrière-plan). Remplacement systématique par des icônes SVG `lucide-react`, déjà la bibliothèque d'icônes établie du projet. Les composants partagés (`KPITile`, `EmptyState`, `QuestCard`, `AchievementToast`, `AIBadge`, medailles de `gamification.tsx`) ont vu leur prop `icon` retypée de `string` vers `ReactNode` pour qu'aucun futur appel ne puisse réintroduire un emoji sous forme de chaîne par défaut.
- **Gamification** : conservée mais **cantonnée** aux écrans où elle a un sens pédagogique direct (tableau de bord élève, hero de la landing page) plutôt que déployée comme langage visuel par défaut sur les tableaux de bord administratifs (établissement, ministériel) et sur les pages de gestion (recrutement, contrats, actes). Exemple : le badge XP flottant sur chaque carte de cours a été remplacé par une puce neutre « Quiz disponible » — l'information reste visible sans dominer visuellement une page de consultation de cours.
- **3D réel** : ajout d'un composant `Tilt3D` (tilt de carte réactif au curseur, calcul de `rotateX`/`rotateY` en direct, glare optionnel, respect de `prefers-reduced-motion`), utilisé sur la carte de progression de la landing page, en remplacement d'un effet 3D statique (transform CSS figé).

## Alternatives considérées
- **Rewrite complet des ~40 fichiers de pages** avec de nouveaux noms de variables sémantiques : écarté pour ce lot — le gain de clarté ne justifiait pas le risque de régression sur un si grand nombre de fichiers déjà fonctionnels ; les noms existants sont conservés, seules leurs valeurs et les usages ponctuels incohérents (bordures dures oubliées, `var(--error)` non définie) ont été corrigés au fil de la relecture fichier par fichier.
- **Suppression totale de la gamification** : écartée — l'utilisateur n'a jamais demandé de retirer XP/niveaux/séries, seulement de corriger le ton d'ensemble ; ces mécaniques restent un différenciateur pédagogique valable pour les élèves, seule leur **portée** a été réduite aux contextes pertinents.
- **Copie littérale de la charte LuluFiles (dark-mode SaaS)** : écartée — l'utilisateur a explicitement demandé une référence d'*impression*, pas une identité visuelle identique ; LuluSchools garde son thème clair par défaut avec bascule sombre, sa propre palette verte de marque et son propre wordmark.

## Conséquences
Facilite : cohérence visuelle et perception de sérieux/fiabilité attendue d'un service public numérique ; accessibilité WCAG facilitée par les bordures fines et les icônes vectorielles (contraste et redimensionnement plus prévisibles qu'un glyphe emoji dépendant de la police système/OS) ; base de composants (`KPITile`, `EmptyState`, etc.) désormais impossible à re-polluer avec des emojis par défaut de type.
Coûte : ce lot ne renomme pas les variables CSS historiques (`--reward`, `--magic`) malgré leur nom devenu trompeur pour certaines (`--magic` ne désigne plus une couleur violette) — à documenter pour toute personne reprenant le projet, et à renommer explicitement si une Phase 2 retouche en profondeur le design system.
