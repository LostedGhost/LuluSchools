# Déploiement — Render (backend) + Vercel (frontend)

Voir `docs/adr/ADR-006-deploiement-render-vercel.md` pour les décisions et leurs justifications. Ce document couvre uniquement les étapes manuelles que `render.yaml` et `frontend/vercel.json` ne peuvent pas faire seuls.

## ⚠️ Action immédiate : rotation d'un secret exposé

Un ancien commit de `render.yaml` (avant la mise en place du Blueprint `databases:` ci-dessous) a contenu en clair l'URL de connexion PostgreSQL, mot de passe inclus. Le fichier est corrigé (voir § 1), mais **ce mot de passe reste visible dans l'historique Git tant que le dépôt n'est pas nettoyé**. Deux actions à faire dès que possible côté Render :
1. Si la base `luluschools-db` créée avec cet ancien mot de passe existe encore : la supprimer et la recréer (le Blueprint ci-dessous la recrée automatiquement via `fromDatabase`) — c'est plus simple et plus sûr que de tenter de faire tourner le mot de passe d'une base existante.
2. Si le dépôt GitHub est **public**, envisager un nettoyage de l'historique (`git filter-repo` ou BFG Repo-Cleaner) pour retirer définitivement le secret des anciens commits — action destructrice (réécrit l'historique, nécessite un force-push) à ne faire qu'après en avoir discuté, voir avec l'équipe si d'autres personnes ont déjà cloné le dépôt.

## 1. Backend (Render)

1. Sur [render.com](https://render.com) : **New > Blueprint**, connecter le dépôt GitHub `LostedGhost/LuluSchools`, branche `main`. Render lit `render.yaml` à la racine et crée **à la fois** le service web `luluschools-backend` et la base PostgreSQL `luluschools-db` (plan gratuit pour les deux).
2. Render demande les variables marquées `sync: false` — les renseigner avec les vraies valeurs (jamais commitées) : `FREELLM_API_KEY`, `LULUFILES_API_KEY`, `KKIAPAY_PUBLIC_KEY`, `KKIAPAY_PRIVATE_KEY`, `KKIAPAY_SECRET`, `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`. `JWT_SECRET_KEY` et `CASIER_JUDICIAIRE_ENCRYPTION_KEY` sont générées automatiquement par Render (`generateValue: true`) — rien à saisir.
3. Lancer le déploiement. `startCommand` applique les migrations Alembic avant de démarrer — vérifier les logs de build pour confirmer qu'elles passent.
4. Une fois en ligne, noter l'URL réelle du service (`https://<nom>.onrender.com` — le nom peut différer de `luluschools-backend` si déjà pris sur Render).
5. **Brevo** : comme en développement, Brevo peut bloquer les e-mails avec *"unrecognised IP address"* tant que l'IP sortante de Render n'est pas autorisée. Récupérer l'IP dans les logs d'erreur Brevo (ou dans le dashboard Render > Outbound IPs) et l'ajouter dans [app.brevo.com/security/authorised_ips](https://app.brevo.com/security/authorised_ips).
6. **Seed du premier compte A++** : Render ne s'exécute pas en shell interactif par défaut. Utiliser l'onglet **Shell** du service Render (ou `render ssh` en CLI) pour lancer une fois :

   ```bash
   python scripts/seed_admin_ministeriel.py "Nom" "Prenom" "email@exemple.bj"
   ```

   Communiquer le mot de passe temporaire affiché de façon sécurisée à la personne concernée (elle devra le changer à la première connexion).

## 2. Frontend (Vercel)

1. Sur [vercel.com](https://vercel.com) : **Add New > Project**, importer le même dépôt.
2. **Root Directory** : choisir `frontend` (dépôt monorepo — Vercel doit builder ce sous-dossier, pas la racine).
3. Framework preset : Vercel détecte Vite automatiquement (`npm run build`, dossier `dist`).
4. **Variables d'environnement** (Project Settings > Environment Variables) : `VITE_KKIAPAY_PUBLIC_KEY` avec la vraie clé publique Kkiapay. `VITE_KKIAPAY_SANDBOX=false` en production. Ce sont des variables *build-time* Vite — un redéploiement est nécessaire après tout changement.
5. Déployer. Noter le domaine attribué (`https://<projet>.vercel.app`, ou un domaine personnalisé si configuré).
6. **Mettre à jour `frontend/vercel.json`** avec l'URL réelle du backend Render (étape 1.4) si elle diffère de `luluschools-backend.onrender.com`, puis commit + push (Vercel redéploie automatiquement).
7. **Mettre à jour `render.yaml`** (`CORS_ALLOW_ORIGINS`) avec le domaine Vercel réel de l'étape 5, puis commit + push (Render redéploie automatiquement). Tant que ce n'est pas fait, les appels directs au backend depuis un navigateur sur ce domaine seraient bloqués par CORS — le flux normal via le rewrite Vercel fonctionne néanmoins dès le premier déploiement, puisqu'il n'implique aucun appel cross-origin côté navigateur.

## 3. Kkiapay

Une fois le backend en ligne, configurer l'URL de webhook **unique pour tout le compte** (pas par transaction) dans le dashboard Kkiapay (Clés API > Webhook) :

```
https://<domaine-backend-render>/api/v1/paiements/webhook/kkiapay
```

Le secret partagé (`x-kkiapay-secret`) doit être exactement la valeur de `KKIAPAY_SECRET` déjà renseignée à l'étape 1.2.

## 4. Vérification post-déploiement

- `GET https://<backend>/api/v1/health` doit répondre `{"status":"ok","checks":{"database":true}}`.
- Se connecter au frontend Vercel, vérifier que les appels `/api/v1/...` passent bien par le rewrite (onglet Réseau du navigateur : les requêtes doivent apparaître sur le domaine Vercel, pas directement sur `onrender.com`).
- Rejouer au moins le parcours tuteur → inscription → validation A+ pour confirmer que la chaîne complète (Vercel → rewrite → Render → PostgreSQL → Brevo/FreeLLM/LuluFiles) fonctionne en conditions réelles.

## 5. CI/CD

- **Tests/build** : `.github/workflows/backend-ci.yml` (pytest + vérification que les migrations Alembic s'appliquent sur un vrai Postgres jetable) et `frontend-ci.yml` (lint + build) tournent sur chaque push/PR touchant leur dossier respectif. Ils bloquent uniquement la visibilité (statut vert/rouge sur GitHub) — ni l'un ni l'autre ne déploie : c'est volontaire, le déploiement reste géré nativement par Render (`autoDeployTrigger: commit`) et par l'intégration GitHub de Vercel, qui redéploient automatiquement à chaque push sur `main` une fois les comptes connectés (étapes 1 et 2).
- Un push sur `main` qui casse les tests backend ou le build frontend part donc quand même en déploiement (Render/Vercel n'attendent pas GitHub Actions) — la CI sert d'alerte rapide, pas de garde-fou bloquant, sauf si une protection de branche est activée côté GitHub (Settings > Branches > Require status checks) pour exiger que ces workflows passent avant de merger une PR.

## Limites du plan gratuit à connaître

- **Base PostgreSQL gratuite Render : expire 30 jours après sa création**, puis 14 jours de grâce avant suppression **définitive** (pas de sauvegarde automatique sur ce plan). Avant l'échéance, soit passer la base sur un plan payant depuis le dashboard Render, soit exporter/réimporter manuellement (`pg_dump` puis `psql` sur une base fraîche). À planifier explicitement si le pilote dépasse quelques semaines — ce n'est pas un plan viable pour une donnée qu'on ne veut pas perdre au-delà de ce délai.
- **Service web gratuit** : se met en veille après 15 minutes sans trafic ; la requête suivante réveille le service en ~50s (page de chargement affichée côté navigateur pendant ce temps).
- **Pas de disque persistant** sur le plan gratuit : le casier judiciaire n'est donc plus écrit sur le disque local du service (il serait perdu à chaque redémarrage/veille) mais chiffré (Fernet, clé `CASIER_JUDICIAIRE_ENCRYPTION_KEY` générée par Render) et stocké directement dans la base PostgreSQL, qui persiste indépendamment du service web — voir ADR-006 pour la justification légale (Art. 395) de ce choix `[Délégué]`.
- Ces limites (expiration DB, veille, pas de disque) sont acceptables pour une démo/un pilote court ; prévoir un passage sur des plans payants (Render "Starter" pour le service + la base) avant tout usage réel prolongé ou toute donnée qu'on ne peut pas se permettre de perdre.
