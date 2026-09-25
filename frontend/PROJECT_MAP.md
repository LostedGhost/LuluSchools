# frontend/ — Project Map

## Stack
Vite + React 19 + TypeScript, Tailwind CSS v4 (`@tailwindcss/vite`, pas de `tailwind.config.js` — voir `vite.config.ts`), `react-router-dom` (routing), `axios` (client API). Pas de librairie de gestion de formulaire/état serveur (React Query, etc.) — le volume de la Phase 1 ne le justifie pas encore ; a réévaluer si la duplication de logique de fetch devient un problème réel.

Le serveur de dev proxy `/api` vers `http://127.0.0.1:8000` (backend local) — voir `vite.config.ts`. En production, le frontend et le backend seront servis derrière le même reverse proxy Nginx (ADR-001), donc `/api/v1/...` restera un chemin relatif valide sans changement de code.

## Arborescence
- `src/types/api.ts` — types TS miroir des schémas Pydantic du backend (contrat : `docs/contrat-api-phase1.md`). Tenu à jour manuellement, pas de génération automatique (OpenAPI codegen) pour l'instant.
- `src/api/` — un module par domaine backend (`auth.ts`, `etablissements.ts`, `inscriptions.ts`, `pedagogie.ts`, `evaluations.ts`, `actes.ts`), chacun exposant des fonctions typées autour de l'instance axios `client.ts`.
- `src/api/client.ts` — instance axios avec intercepteur d'auth (Bearer token depuis `localStorage`) et rafraîchissement automatique du token sur 401 (refresh token, un seul refresh en vol partagé entre requêtes concurrentes via `refreshEnCours`).
- `src/auth/AuthContext.tsx` — état d'authentification global (`utilisateur: MeOut | null`), `seConnecter`/`seDeconnecter`/`rafraichirUtilisateur`.
- `src/auth/RequireAuth.tsx` — garde de route : redirige vers `/connexion` si non authentifié, vers `/changer-mot-de-passe` si `mot_de_passe_temporaire=true` (bloque l'accès au reste de l'app tant que ce n'est pas fait, cohérent avec `get_current_active_user` côté backend), filtre par rôle (`roles` prop).
- `src/eleve/EleveProfileContext.tsx` — contexte séparé de `AuthContext` : charge `GET /eleves/me` une fois par montage de route élève (matricule, classe actuelle) ; toutes les pages élève en dépendent pour connaître leur `classe_id`.
- `src/layout/AppLayout.tsx` — en-tête + navigation, adaptée au rôle courant (`navPourRole`).
- `src/components/ui.tsx` — kit d'UI minimal partagé (Card, boutons, champs, badges, bannière d'erreur) — pas de librairie de composants externe.
- `src/components/KkiapayButton.tsx` — charge le script `https://cdn.kkiapay.me/k.js` à la demande et ouvre le widget Kkiapay (`openKkiapayWidget`/`addSuccessListener`/`addFailedListener`). Clé publique et mode sandbox lus depuis `VITE_KKIAPAY_PUBLIC_KEY`/`VITE_KKIAPAY_SANDBOX` (voir `.env.example`) — jamais la clé privée, qui reste backend-only.
- `src/pages/` — une page par écran, organisées par rôle (`tuteur/`, `eleve/`) ou transverses (`LoginPage`, `SignupTuteurPage`, `ChangePasswordPage`, `DashboardRedirect`).

## Parcours construits (étape 6)
- **Tuteur** : `SignupTuteurPage` (inscription + vérification OTP), `TuteurDashboard` (liste des enfants et statut via `GET /tuteurs/me/inscriptions`, don de consentement parental), `NouvelleInscriptionPage` (choix établissement → classe → formulaire enfant).
- **Élève** : `EleveDashboard`, `CoursListPage` + `QuizPage` (quiz généré par IA, tentatives illimitées, historique via `GET /quiz/{id}/mes-tentatives`), `DevoirsListPage` + `DevoirDetailPage` (soumission d'un devoir puis **suivi en direct de la correction IA en arrière-plan** — `statut=en_correction` affiché immédiatement, `setInterval` de 3s qui relit `GET /devoirs/{id}/ma-soumission` jusqu'à résolution, cohérent avec ADR-005), `BulletinPage` (sélecteur de trimestre), `ActesPage` (demande d'acte du catalogue ou réclamation, paiement Kkiapay pour les actes payants).

Non construits : Enseignant, A+ (admin établissement), A++ (admin ministériel), écrans de révision manuelle (candidatures/soumissions en échec IA).

## Validé en navigateur réel (pas seulement `npm run build`)
Le parcours Tuteur/Élève complet a été rejoué manuellement dans le navigateur (built-in browser tool), contre une instance réelle du backend (`uvicorn`) et la vraie base PostgreSQL, **sans mocks** : création de compte tuteur (e-mail réel envoyé via Brevo), connexion, changement de mot de passe temporaire, création d'une inscription, validation par un A+ (via API, écran A+ pas encore construit), connexion élève par matricule, consultation d'un cours, génération réelle d'un quiz par FreeLLM et tentative notée, soumission d'un devoir et correction réelle par FreeLLM en arrière-plan (suivie via le polling jusqu'au résultat final), bulletin pondéré calculé correctement, et soumission d'une réclamation de note. **A révélé un vrai bug backend** (`DocumentCandidatureOut` sans `id`, rendant l'écran de révision manuelle inutilisable — corrigé, voir `backend/PROJECT_MAP.md`).

## Notes
- `.env.example` documente `VITE_KKIAPAY_PUBLIC_KEY`/`VITE_KKIAPAY_SANDBOX` — `.env` local non commité (gitignore racine).
- `.claude/launch.json` (racine du dépôt) définit le serveur de dev `frontend` pour `preview_start`, sur le port 5173.
- Pas de tests automatisés frontend pour l'instant (ni unitaires ni end-to-end) — seule la validation manuelle en navigateur ci-dessus existe. À évaluer avant la mise en production (Playwright ou équivalent).
