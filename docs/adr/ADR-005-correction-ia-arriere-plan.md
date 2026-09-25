# ADR-005 : Notation/correction IA exécutée en arrière-plan (BackgroundTasks)

## Statut
Accepté (décision technique déléguée à l'implémentation par l'utilisateur : "La correction IA sera synchrone ou asynchrone selon ce que tu trouves logique").

## Contexte
Deux flux du backend appellent FreeLLM plusieurs fois au sein d'une seule requête HTTP :
- `POST /postes/{id}/candidatures` (UC-04) : un appel `noter_document` par document de candidature (2 à N documents selon les critères du poste).
- `POST /devoirs/{id}/soumissions` (UC-08) : un appel `corriger_reponse` par question du devoir.

FreeLLM agrège des modèles gratuits sans SLA ni garantie de latence (ADR-002). Exécutés en série et de façon synchrone dans le corps de la requête, ces appels peuvent cumuler plusieurs secondes, voire échouer par timeout, bloquant l'utilisateur (élève ou enseignant) qui attend simplement une confirmation de soumission/candidature.

À l'inverse, la génération de quiz (`POST /cours/{id}/quiz`, UC-07) ne fait qu'**un seul** appel FreeLLM par requête : le risque de latence cumulée n'existe pas, et l'enseignant veut voir immédiatement le quiz généré pour le relire avant publication.

## Décision
- `postuler` (candidatures) et `soumettre_devoir` (soumissions) : l'upload/l'enregistrement reste synchrone (nécessaire pour renvoyer un objet exploitable immédiatement), mais la notation/correction IA proprement dite part en tâche de fond via `fastapi.BackgroundTasks`, après la réponse HTTP. L'objet renvoyé porte un statut "en attente" (`DocumentCandidature.statut=en_attente`, nouveau `StatutSoumission.EN_CORRECTION`) ; le client relit l'état final via `GET /candidatures/{id}` ou le nouvel endpoint `GET /soumissions/{id}`.
- `generer_quiz` (`POST /cours/{id}/quiz`) : reste synchrone, un seul appel réseau, réponse immédiate exploitable par l'enseignant.
- La tâche de fond ouvre sa **propre session DB** (celle de la requête est déjà fermée au moment où `BackgroundTasks` s'exécute) via une fabrique de session injectable (`Depends(get_session_factory)`), et réutilise le **même client FreeLLM** déjà résolu par `Depends(get_llm_client)` au moment de la requête — jamais reconstruit dans la tâche de fond, ce qui préserve l'injection de dépendance utilisée par les tests (`FakeLLMClient`) sans appel réseau réel en environnement de test.

## Alternatives considérées
- **Tout garder synchrone** (implémentation initiale) : simple, mais expose l'utilisateur à des requêtes potentiellement longues (plusieurs secondes à dizaines de secondes selon le nombre de documents/questions) sans aucune garantie de FreeLLM (ADR-002 : pas de SLA, pas de modèle frontier).
- **File de tâches externe (Celery/Redis, etc.)** : sur-dimensionné pour le volume Phase 1 pilote ; ADR-001 a déjà tranché pour un monolithe modulaire sans dépendance d'infrastructure supplémentaire (pas de Docker, pas de service de queue externe). `BackgroundTasks` (in-process, déjà dans FastAPI) suffit à ce stade et reste cohérent avec APScheduler déjà retenu pour les tâches planifiées.
- **Tout passer en arrière-plan (y compris le quiz)** : inutile, un seul appel réseau ne pose pas de problème de latence cumulée, et l'enseignant bénéficie d'un retour immédiat pour ajuster le quiz avant publication.

## Conséquences
Facilite : la requête de soumission/candidature répond rapidement, sans dépendre de la latence de FreeLLM ; le pattern (documents/réponses en attente, filet de secours de révision manuelle déjà existant pour les échecs) s'étend naturellement à l'état "en cours de traitement".
Rend plus coûteux/risqué : le frontend doit **relire** l'objet après soumission pour connaître le résultat final (pas de long-polling ni de websocket prévu en Phase 1 — un simple `GET` déclenché après la soumission, ou au chargement de l'écran de suivi, suffit) ; en cas de crash serveur entre la réponse HTTP et l'exécution de la tâche de fond, la notation resterait bloquée `en_attente`/`en_correction` indéfiniment (`BackgroundTasks` n'a pas de mécanisme de retry ni de persistance de la tâche elle-même — seul l'état déjà en base est fiable) - acceptable pour le volume Phase 1 pilote, à réévaluer (retry, file persistante) si des incidents de ce type sont observés en production.
