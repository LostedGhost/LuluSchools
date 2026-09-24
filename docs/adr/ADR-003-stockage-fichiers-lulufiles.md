# ADR-003 : Stockage de fichiers via LuluFiles

## Statut
Accepté (révise le point "stockage de fichiers" d'ADR-001, qui envisageait le système de fichiers local du serveur pour tous les documents).

## Contexte
L'utilisateur impose **LuluFiles** (https://lulufiles-api.onrender.com, repo personnel) comme couche de stockage de fichiers de la plateforme. Particularité : les octets des fichiers sont physiquement stockés dans un salon Telegram (via un bot), pas sur les serveurs de LuluFiles — chaque upload/download transite par LuluFiles puis Telegram, hors du territoire béninois. Le plan actuel ("Lancement", gratuit) limite le compte à 5 Go de transfert mensuel et 2 Mo/s de bande passante, partagés par l'ensemble des utilisateurs finaux.

Cette contrainte technique croise une question déjà posée en UC-04 (`cas-utilisation-phase-1.md`) : le régime restreint du casier judiciaire (Art. 395 de la loi n° 2017-20) interdit son traitement par des acteurs hors juridictions/auxiliaires de justice/finalités légales précises, et exige qu'un registre de condamnations pénales reste "sous le contrôle de l'Autorité publique" — un service tiers étranger ne l'est pas.

## Décision
LuluFiles est utilisé comme stockage de fichiers pour **tous les documents de la plateforme à l'exception du casier judiciaire** : contenus pédagogiques (UC-06), CV/diplômes de candidature (UC-04, hors casier judiciaire), soumissions de devoirs (UC-08), documents produits pour les actes académiques (UC-10).

Le **casier judiciaire reste exclu de LuluFiles** et continue d'être stocké sur le système de fichiers local du serveur, avec l'accès restreint aux personnes désignées par l'A+ déjà décidé en UC-04 — Art. 395 ne prévoit aucune dérogation par consentement, contrairement au reste des données personnelles (Art. 392).

Base légale du transfert international pour les fichiers concernés : **consentement explicite** de la personne concernée (Art. 392-1°), ajouté au flux de consentement déjà prévu à l'inscription/la création de compte (Art. 415-424 — transparence). Le fait que les fichiers transitent par un prestataire tiers dont l'infrastructure de stockage se trouve hors du Bénin doit être explicitement mentionné dans cette information.

Organisation technique : un seul disque LuluFiles pour la Phase 1 (extensible plus tard si besoin, par ex. un disque par environnement), stockage **à plat** (pas d'arborescence de dossiers côté LuluFiles) — c'est le modèle relationnel PostgreSQL de LuluSchools qui reste la source de vérité de l'organisation des fichiers (par établissement, classe, candidature, élève), conformément à la recommandation de LuluFiles elle-même quand une application a déjà son propre modèle. Chaque entité qui référence un fichier stocke `lulufiles_file_id` (UUID), pas un chemin local ni une URL brute.

## Alternatives considérées
- **Système de fichiers local du serveur pour tout** (décision initiale d'ADR-001) : révisée sur demande explicite de l'utilisateur, qui a créé LuluFiles pour ce projet.
- **LuluFiles pour tous les documents, casier judiciaire inclus** : écarté — Art. 395 ne prévoit pas de dérogation par consentement, contrairement au reste des données personnelles ; stocker un casier judiciaire via un canal privé étranger serait une non-conformité difficilement défendable.
- **Arborescence de dossiers LuluFiles reflétant établissement/classe** : écartée pour l'instant — complexité inutile (profondeur max 32, unicité des noms de dossier, coût de déplacement inter-disque) alors que PostgreSQL organise déjà tout ; à reconsidérer seulement si un usage humain direct de l'arborescence LuluFiles (hors application) devient nécessaire.

## Conséquences
Facilite : pas d'infrastructure de stockage à gérer soi-même, déduplication automatique, pas de dépendance Docker (service distant).
Rend plus coûteux/risqué : (1) le plan gratuit actuel (5 Go/mois, 2 Mo/s partagés par tout le compte) est un goulot d'étranglement réel pour un déploiement au-delà d'un pilote restreint — à surveiller via `GET /me/usage` et à réévaluer avant la Phase 2/3 ; (2) le transfert international de données personnelles nécessite une information/consentement explicite ajoutée au flux d'inscription, sujette à vérification par l'APDP en cas de contrôle ; (3) le casier judiciaire nécessite un chemin de stockage séparé (déjà prévu), ce qui exclut une implémentation uniforme "tout passe par LuluFiles".
