# Suivi de projet — LuluSchools

Copier ce fichier au démarrage du projet et cocher au fur et à mesure des validations. Chaque case cochée correspond à un artefact réellement produit et validé, pas juste "commencé". Méthode : pipeline spec-first `lucio-dev`.

- [x] **1. Cas d'utilisation** — liste complète, validée explicitement (Phase 1 — voir `docs/cas-utilisation-phase-1.md`)
- [x] **2. Diagrammes UML** — diagramme de cas d'utilisation + diagramme de classes, validés — voir `docs/diagrammes-uml-phase1.md`
- [x] **3. Choix technique et contrat d'API** — stack retenue et contrat d'API validés — voir `README.md`, `docs/choix-technique-phase1.md`, `docs/contrat-api-phase1.md`, `docs/adr/`
- [ ] **4. Backend** — tous les endpoints développés, testés et documentés, un par un (en cours : `GET /health` fait, voir `docs/contrat-api-phase1.md`)
- [ ] **5. Validation complète du backend** — test de bout en bout réalisé (Postman ou équivalent)
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
