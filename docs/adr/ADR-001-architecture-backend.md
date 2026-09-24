# ADR-001 : Style architectural du backend LuluSchools

## Statut
Accepté

## Contexte
Backend FastAPI + PostgreSQL, frontend React et paiement Kkiapay imposés par l'utilisateur. Contrainte forte : pas de Docker disponible sur la machine de développement, donc aucune techno qui l'impose. Projet piloté par un seul développeur, sous mandat ministériel (Bénin), destiné à durer plusieurs années, démarrant sur un périmètre pilote (Phase 1) avant extension nationale (Phases 2-3). Le diagramme de classes de la Phase 1 est déjà validé (identité/RBAC, inscriptions, recrutement/contrats, pédagogie, évaluations, actes académiques).

## Décision
Monolithe modulaire : un seul déploiement FastAPI, découpé en modules métier alignés sur les diagrammes de classes validés (`identite/`, `inscriptions/`, `recrutement/`, `pedagogie/`, `evaluations/`, `actes/`). Pattern interne en couches (routers → services → repositories/models) à l'intérieur de chaque module. Une seule base PostgreSQL partagée. Pas de queue/broker : tâches planifiées via APScheduler in-process + FastAPI BackgroundTasks. Fichiers stockés sur le système de fichiers du serveur, accès toujours médié par le backend.

## Alternatives considérées
- **Monolithe simple (un seul dossier plat)** : écarté — avec 6 modules métier et 3 phases prévues, la navigation deviendrait vite confuse sans frontières internes.
- **Microservices** : écarté — coût opérationnel (déploiements multiples, observabilité distribuée, cohérence de données inter-services) injustifié pour un solo dev sans Docker ni infra DevOps mature ; à reconsidérer seulement si plusieurs équipes autonomes émergent après la Phase 3.
- **Clean/Hexagonal Architecture** : écarté pour l'instant — la logique métier de Phase 1 est riche en règles mais FastAPI/SQLAlchemy sont des choix durables, pas des dépendances à isoler par excès de prudence. Réévaluable si un module (ex. recrutement/scoring) devient un vrai cœur métier à tester en isolation totale.
- **Base de données par module** : écarté — les entités sont trop interconnectées (`Eleve` traverse presque tous les modules) pour justifier la complexité d'un découpage.
- **Celery + Redis pour les tâches planifiées** : écarté pour la Phase 1 — ajoute un service supplémentaire à faire tourner sans Docker, alors qu'APScheduler in-process suffit au volume attendu.

## Conséquences
Facilite : mise en route rapide sans Docker, cohérence transactionnelle simple (une seule base, un seul processus), extraction future en microservices possible si le besoin se confirme (les frontières de module existent déjà).
Rend plus coûteux : un scaling horizontal différencié par module (tout scale ensemble) ; à réévaluer explicitement si un module (ex. notation IA) devient un goulot d'étranglement identifié.
