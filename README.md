# SmartCampus AI

Plateforme agentique d'orientation universitaire (IIT / ISB).

## Stack
- Backend : FastAPI (Python)
- Frontend : Next.js (React, TypeScript, Tailwind)
- Base de donnÃ©es : PostgreSQL (Ã  venir)

## Structure
- backend/ : API FastAPI
- frontend/ : application Next.js
- database/ : schÃ©ma et migrations
- docs/ : architecture et documentation

## Base de donnÃ©es et Migrations
Pour initialiser la base de donnÃ©es et appliquer toutes les migrations (les 22 tables) :
```bash
docker compose up -d
cd backend
python -m alembic upgrade head      # CrÃ©e et applique les 22 tables + alembic_version
python -m pytest tests/test_schema.py
```

## Lancement avec Docker (recommandÃ©)
1. Copier backend/.env.example en backend/.env
2. Copier frontend/.env.example en frontend/.env.local
3. Depuis la racine : docker compose up --build

## DonnÃ©es de dÃ©monstration (fictives)
cd backend
python -m scripts.seed          # idempotent, relanÃ§able sans doublons

Comptes de dÃ©mo (dÃ©veloppement uniquement) :
| Email | RÃ´le |
|---|---|
| responsable.iit@smartcampus.local | responsable IIT |
| responsable.isb@smartcampus.local | responsable ISB |
| candidat.demo@smartcampus.local | candidat |

Mot de passe par dÃ©faut : voir DEFAULT_DEMO_PASSWORD dans backend/scripts/seed.py.
Pour le changer (PowerShell) : $env:SEED_DEMO_PASSWORD="votre_valeur"; python -m scripts.seed

Cas de test inclus : le Master ISB est en `brouillon` et un tarif ISB 2025-2026 est expirÃ©,
pour vÃ©rifier que les API ne servent que les informations publiÃ©es et valides.

## Lancement sans Docker
Backend :
  cd backend
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  copy .env.example .env
  fastapi dev app/main.py

Frontend (dans un autre terminal) :
  cd frontend
  npm install
  copy .env.example .env.local
  npm run dev

## URLs
- Application : http://localhost:3000
- Documentation de l'API : http://localhost:8000/docs

## Comment ajouter une fonctionnalitÃ©
Backend :
- CrÃ©er un fichier dans backend/app/api/v1/endpoints/ (copier health.py)
- Le dÃ©clarer dans backend/app/api/v1/router.py
- SchÃ©mas dans app/schemas/, logique dans app/services/, modÃ¨les dans app/models/
- Ajouter un test dans backend/tests/
Frontend :
- Nouvelle page : frontend/src/app/nom-page/page.tsx
- Composants dans frontend/src/components/
- Appels API avec apiFetch de frontend/src/lib/api.ts

## Conventions Git
- Une story = une branche : feature/SA-X-nom-court
- Commits : "SA-X: description"
- Toujours une Pull Request, jamais de push direct sur main
- Ne jamais commiter .env, .venv ou node_modules

## Sessions visiteurs (conversation sans compte)

Un visiteur peut discuter sans crÃ©er de compte : une session temporaire est crÃ©Ã©e automatiquement.

| RÃ©glage (`backend/.env`) | DÃ©faut | RÃ´le |
|---|---|---|
| `SESSION_TTL_MINUTES` | 120 | durÃ©e de validitÃ© d'une session |
| `SESSION_MAX_MESSAGES` | 50 | messages visiteur max par session |
| `SESSION_MAX_CONVERSATIONS` | 3 | conversations max par session |

Endpoints :
| MÃ©thode | Route | RÃ´le |
|---|---|---|
| POST | `/api/v1/sessions` | crÃ©e une session et renvoie le token (affichÃ© une seule fois) |
| GET | `/api/v1/sessions/me` | Ã©tat de la session : temps, messages et conversations restants |
| DELETE | `/api/v1/sessions/me` | termine la session |

Le token est envoyÃ© dans l'en-tÃªte `X-Session-Token`. Seul son hash SHA-256 est stockÃ© en base.
Pour protÃ©ger une route : `session = Depends(get_current_session)` (401 si absente ou expirÃ©e).
Pour limiter l'usage : `verifier_quota_messages(db, session)` ou `verifier_quota_conversations(db, session)` (429 si la limite est atteinte), dans `app/services/quota_service.py`.

Expiration : une session dÃ©passÃ©e passe Ã  `expiree` dÃ¨s sa prochaine utilisation. La purge supprime
les sessions expirÃ©es depuis plus de 7 jours avec leurs conversations et messages :

    cd backend
    python -m scripts.purge_sessions     # Ã  planifier rÃ©guliÃ¨rement

Frontend : `frontend/src/lib/session.ts` (`ensureSession`, `sessionFetch`, `endSession`) crÃ©e,
rÃ©utilise et renouvelle la session ; le token est gardÃ© dans le `localStorage` du navigateur.

Tests : `python -m pytest tests/test_session_service.py tests/test_session_deps.py tests/test_sessions_api.py tests/test_quota_service.py tests/test_session_purge.py`


## MÃ©moire temporaire des conversations

L'agent IA garde le contexte d'une conversation sans redemander les mÃªmes informations.
Tout est temporaire et limitÃ© :

| RÃ©glage (`backend/.env`) | DÃ©faut | RÃ´le |
|---|---|---|
| `MEMOIRE_TTL_MINUTES` | 60 | durÃ©e de vie d'un message (jamais au-delÃ  de la session) |
| `MEMOIRE_MAX_MESSAGES_STOCKES` | 100 | messages gardÃ©s par conversation (les plus anciens sont supprimÃ©s) |
| `MEMOIRE_FENETRE_MESSAGES` | 10 | derniers messages donnÃ©s Ã  l'IA comme contexte |
| `MEMOIRE_MAX_CARACTERES` | 2000 | taille maximale d'un message conservÃ© |

Deux niveaux de mÃ©moire :
- **Messages** (table `message`) : `ajouter_message(...)` les enregistre avec une date d'expiration ;
  `get_historique(...)` retourne les derniers non expirÃ©s, et `historique_pour_llm(...)` les met au
  format `[{"role": ..., "content": ...}]` attendu par un LLM.
- **Informations utiles** (colonne `conversation.memoire`) : niveau, section du bac, moyenne, matiÃ¨res
  prÃ©fÃ©rÃ©es, centres d'intÃ©rÃªt, objectif, contraintes. `mettre_a_jour_memoire(...)` fusionne les
  nouvelles informations (champs et tailles contrÃ´lÃ©s) et `infos_manquantes(...)` indique ce que
  l'agent peut encore demander. Ces informations disparaissent avec la session.

Le code est dans `backend/app/services/memoire_service.py`. Endpoints (en-tÃªte `X-Session-Token`) :
| MÃ©thode | Route | RÃ´le |
|---|---|---|
| POST | `/api/v1/conversations` | ouvre une conversation (429 si limite atteinte) |
| POST cd D:\Projet_IA\SmartCampus_IEEA
$utf8 = New-Object System.Text.UTF8Encoding $false
$c = Get-Content README.md -Raw
$c = $c.Replace('python -m pytest tests/test_schema.py', ('python -m pytest tests/test_schema.py' + "`n" + '```'))
[IO.File]::WriteAllText("$PWD\README.md", $c, $utf8)
Select-String -Path README.md -Pattern '^```'| `/api/v1/conversations/{id}/messages` | enregistre un message du visiteur |
| GET | `/api/v1/conversations/{id}/messages` | derniers messages non expirÃ©s |
| GET | `/api/v1/conversations/{id}/memoire` | informations retenues et informations manquantes |
| DELETE | `/api/v1/conversations/{id}/memoire` | droit Ã  l'oubli : efface messages et informations |

Une conversation n'est accessible que par sa propre session (404 sinon).
La purge (`python -m scripts.purge_sessions`) supprime aussi les messages expirÃ©s.
Frontend : `frontend/src/lib/conversation.ts` (`ensureConversation`, `sendMessage`, `getMessages`,
`getMemoire`, `forgetConversation`).
