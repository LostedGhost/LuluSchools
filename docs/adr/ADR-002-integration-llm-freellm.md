# ADR-002 : Accès aux LLM du projet via FreeLLM

## Statut
Accepté

## Contexte
UC-04 (candidature enseignant) nécessite un modèle d'IA pour lire et noter automatiquement les documents déposés (hors casier judiciaire, traité à part pour raisons légales — voir `cas-utilisation-phase-1.md`). D'autres besoins LLM apparaîtront probablement dans les phases suivantes. L'utilisateur impose l'utilisation de son propre service, **FreeLLM** (https://freellm-lucio.onrender.com, repo https://github.com/LostedGhost/freellm-lucio), pour tous les appels LLM du projet plutôt que l'API Anthropic en direct ou tout autre fournisseur.

FreeLLM agrège des LLM à niveau gratuit (Google, Groq, Cerebras, Mistral, OpenRouter, etc.) derrière une API compatible OpenAI, hébergé à distance (Render) — aucune installation locale requise, donc aucun conflit avec la contrainte "pas de Docker".

## Décision
Tous les appels LLM du backend passent par FreeLLM, via le SDK Python `openai` configuré avec `base_url` et `api_key` (`FREELLM_BASE_URL`, `FREELLM_API_KEY`) lus depuis `.env` — jamais le SDK `anthropic` ni un appel direct à un autre fournisseur.

Pour UC-04 : chaque document (hors casier judiciaire) est envoyé à `POST /v1/chat/completions` avec `model: "auto"` et le contenu en vision (image bytes en base64 — FreeLLM n'accepte que des images en vision, pas nativement le PDF). Les PDF sont donc convertis page par page en images côté backend avant l'appel, via **PyMuPDF** (`pymupdf`, pip pur, aucune dépendance système — contrairement à `pdf2image`/Poppler, cohérent avec l'absence de Docker pour isoler ces libs).

**Règle de repli (nouvelle, opérationnelle)** : FreeLLM n'offre aucun SLA et route vers des modèles non-frontier, avec latence et disponibilité variables. Si l'appel échoue après 3 tentatives (backoff exponentiel) ou renvoie 422 (aucun modèle vision actif), le document ne bloque pas la candidature et n'obtient pas de note inventée : il passe en file de révision manuelle par l'A+, avec le même effet qu'un score en attente. Cette règle s'ajoute à, et ne remplace pas, le droit de recours déjà posé en UC-04b.

## Alternatives considérées
- **API Anthropic en direct** : écartée sur demande explicite de l'utilisateur, qui veut centraliser tous les appels LLM du projet via FreeLLM.
- **Modèle auto-hébergé (Ollama local, etc.)** : écarté — ajouterait une dépendance lourde et locale alors que FreeLLM existe déjà, fonctionne sans Docker (hébergé à distance) et couvre déjà le besoin de vision.

## Conséquences
Facilite : un seul point d'intégration LLM pour tout le projet, coût nul (paliers gratuits), pas de dépendance Docker.
Rend plus coûteux/risqué : qualité de notation plus variable qu'avec un modèle frontier (pas de Claude Opus/GPT-5 disponibles via FreeLLM) — à documenter auprès des A+ comme une aide au tri, jamais une vérité absolue ; absence de SLA nécessitant la file de révision manuelle décrite ci-dessus ; toute évolution du routage interne de FreeLLM (modèles ajoutés/retirés) est hors du contrôle du projet LuluSchools.
