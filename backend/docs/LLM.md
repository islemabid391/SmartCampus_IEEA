# Connexion au LLM (SA-36)

## Configuration (backend/.env, jamais dans Git)

| Variable | Rôle | Défaut |
|---|---|---|
| LLM_API_KEY | clé du fournisseur (secrète, jamais journalisée) | vide |
| LLM_BASE_URL | API compatible OpenAI | https://api.groq.com/openai/v1 |
| LLM_MODEL | modèle utilisé | openai/gpt-oss-20b |
| LLM_TIMEOUT_SECONDES | délai maximal d'une requête | 30 |
| LLM_MAX_TOKENS | longueur maximale de la réponse | 1500 |
| LLM_TEMPERATURE | créativité (bas = précis) | 0.2 |
| LLM_MAX_RETRIES | nouvelles tentatives (timeout, 5xx, réseau) | 2 |

Ollama en local (sans clé) : LLM_BASE_URL=http://localhost:11434/v1, LLM_MODEL=mistral, LLM_TIMEOUT_SECONDES=120.

## API

POST /api/v1/conversations/{id}/chat   (en-tête X-Session-Token)
Corps : {"contenu": "ma question", "langue": "fr"}
Réponse : {"reponse": {...message assistant...}, "modele": "...", "duree_ms": 718, "tronquee": false}

La question et la réponse ne sont enregistrées qu'en cas de succès.

## Erreurs

| Code | Cause |
|---|---|
| 401 / 404 | session invalide / conversation inconnue |
| 429 | quota de messages de la session atteint |
| 503 | LLM non configuré, clé refusée, service indisponible ou saturé |
| 504 | le LLM a mis trop de temps à répondre |
| 502 | réponse du LLM vide ou inexploitable |

Les messages d'erreur ne contiennent jamais la clé, l'URL ni les détails du fournisseur.

## Tests

Les tests utilisent un LLM simulé : aucune clé ni réseau nécessaires (pytest).