# Suivi de projet — LuluSchools

Copier ce fichier au démarrage du projet et cocher au fur et à mesure des validations. Chaque case cochée correspond à un artefact réellement produit et validé, pas juste "commencé". Méthode : pipeline spec-first `lucio-dev`.

- [x] **1. Cas d'utilisation** — liste complète, validée explicitement (Phase 1 — voir `docs/cas-utilisation-phase-1.md`)
- [x] **2. Diagrammes UML** — diagramme de cas d'utilisation + diagramme de classes, validés — voir `docs/diagrammes-uml-phase1.md`
- [x] **3. Choix technique et contrat d'API** — stack retenue et contrat d'API validés — voir `README.md`, `docs/choix-technique-phase1.md`, `docs/contrat-api-phase1.md`, `docs/adr/`
- [x] **4. Backend** — tous les modules Phase 1 faits et testés (identité, établissements, inscriptions, recrutement/contrats, pédagogie, évaluations, actes) — 68 tests passants, dont le mot de passe temporaire réellement appliqué côté serveur. Notation/correction IA reste synchrone dans la requête (acceptable au volume Phase 1) — voir `backend/PROJECT_MAP.md` § zones instables
- [x] **5. Validation complète du backend** — scénario de bout en bout automatisé (`tests/test_e2e_parcours_complet.py`) rejouant UC-01 à UC-10 dans l'ordre réel d'usage, avec les mêmes objets circulant d'un module à l'autre. A révélé et corrigé un vrai bug (chemin du stockage du casier judiciaire mal interprété sous Windows). Portée : logique métier et intégration entre modules validées avec les services externes simulés (Brevo/FreeLLM/LuluFiles/Kkiapay) ; la connectivité réelle à ces services avec les vraies clés n'a pas été testée en conditions réelles — à faire avant mise en production
- [ ] **6. Frontend** — design system, composants de base et pages validés sur données mock
- [ ] **7. Intégration** — backend et frontend réels connectés, écarts corrigés
- [ ] **8. Déploiement** — application déployée et vérifiée en conditions réelles

## Cadrage verrouillé

- Portage : mandat ministériel officiel (Bénin). A++ = acteur gouvernemental réel.
- Zone V1 : Bénin — conformité suivie via le référentiel loi n° 2017-20 (skill `droit-numerique-benin`).
- Paiement / séquestre : Kkiapay (agrégateur mobile money/carte).
- Phasage MVP : Phase 1 (socle identité/inscriptions/contrats/cours/devoirs/moyennes) → Phase 2 (réclamations/actes payants/tickets/messagerie) → Phase 3 (vidéo/live/billetterie/micro-jobs+séquestre/3D).

## Notes / écarts assumés

- **Plan LuluFiles gratuit ("Lancement")** : 5 Go de transfert/mois et 2 Mo/s de bande passante partagés par tout le compte. Choix assumé par l'utilisateur pour la Phase 1 pilote ; passage à un plan payant prévu au besoin, à réévaluer avant la Phase 2/3 (voir `docs/adr/ADR-003-stockage-fichiers-lulufiles.md`).
