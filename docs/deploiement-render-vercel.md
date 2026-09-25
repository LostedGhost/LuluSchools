# Déploiement — Render (backend) + Vercel (frontend)

Voir `docs/adr/ADR-006-deploiement-render-vercel.md` pour les décisions et leurs justifications. Ce document couvre uniquement les étapes manuelles que `render.yaml` et `frontend/vercel.json` ne peuvent pas faire seuls.

## 1. Backend (Render)

1. Sur [render.com](https://render.com) : **New > Blueprint**, connecter le dépôt GitHub `LostedGhost/LuluSchools`, branche `main`. Render lit `render.yaml` à la racine.
2. Render demande les variables marquées `sync: false` — les renseigner avec les vraies valeurs (jamais commitées) : `FREELLM_API_KEY`, `LULUFILES_API_KEY`, `KKIAPAY_PUBLIC_KEY`, `KKIAPAY_PRIVATE_KEY`, `KKIAPAY_SECRET`, `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`.
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

## Limites à connaître

- Le service backend Render doit rester à **une seule instance** (pas d'autoscaling) tant que le casier judiciaire reste sur le disque persistant local — voir ADR-006.
- Plan Render "Starter" : pas de mise en veille contrairement au plan gratuit, mais coût mensuel dès le premier euro (service web + PostgreSQL + disque).
