# LuluSchools — Frontend

Application React (Vite + TypeScript + Tailwind CSS v4) consommant l'API backend LuluSchools.

Voir [PROJECT_MAP.md](PROJECT_MAP.md) pour la structure du code et l'état d'avancement des parcours, et le [README racine](../README.md) pour les instructions de lancement local.

```bash
cp .env.example .env   # renseigner VITE_KKIAPAY_PUBLIC_KEY (cle publique, pas la privee)
npm install
npm run dev             # http://localhost:5173, proxy /api vers le backend local (voir vite.config.ts)
npm run build            # verification des types (tsc -b) + build de production
```
