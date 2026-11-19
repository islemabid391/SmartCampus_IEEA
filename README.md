# SmartCampus AI

Plateforme agentique d'orientation universitaire (IIT / ISB).

## Stack
- Backend : FastAPI (Python)
- Frontend : Next.js (React, TypeScript, Tailwind)
- Base de données : PostgreSQL (à venir)

## Structure
- backend/ : API FastAPI
- frontend/ : application Next.js
- database/ : schéma et migrations
- docs/ : architecture et documentation

## Base de données et Migrations
Pour initialiser la base de données et appliquer toutes les migrations (les 22 tables) :
```bash
docker compose up -d
cd backend
python -m alembic upgrade head      # Crée et applique les 22 tables + alembic_version
python -m pytest tests/test_schema.py

## Lancement avec Docker (recommandé)
1. Copier backend/.env.example en backend/.env
2. Copier frontend/.env.example en frontend/.env.local
3. Depuis la racine : docker compose up --build

## Données de démonstration (fictives)
cd backend
python -m scripts.seed          # idempotent, relançable sans doublons

Comptes de démo (développement uniquement) :
| Email | Rôle |
|---|---|
| responsable.iit@smartcampus.local | responsable IIT |
| responsable.isb@smartcampus.local | responsable ISB |
| candidat.demo@smartcampus.local | candidat |

Mot de passe par défaut : voir DEFAULT_DEMO_PASSWORD dans backend/scripts/seed.py.
Pour le changer (PowerShell) : $env:SEED_DEMO_PASSWORD="votre_valeur"; python -m scripts.seed

Cas de test inclus : le Master ISB est en `brouillon` et un tarif ISB 2025-2026 est expiré,
pour vérifier que les API ne servent que les informations publiées et valides.

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

## Comment ajouter une fonctionnalité
Backend :
- Créer un fichier dans backend/app/api/v1/endpoints/ (copier health.py)
- Le déclarer dans backend/app/api/v1/router.py
- Schémas dans app/schemas/, logique dans app/services/, modèles dans app/models/
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

Un visiteur peut discuter sans créer de compte : une session temporaire est créée automatiquement.

| Réglage (`backend/.env`) | Défaut | Rôle |
|---|---|---|
| `SESSION_TTL_MINUTES` | 120 | durée de validité d'une session |
| `SESSION_MAX_MESSAGES` | 50 | messages visiteur max par session |
| `SESSION_MAX_CONVERSATIONS` | 3 | conversations max par session |

Endpoints :
| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/v1/sessions` | crée une session et renvoie le token (affiché une seule fois) |
| GET | `/api/v1/sessions/me` | état de la session : temps, messages et conversations restants |
| DELETE | `/api/v1/sessions/me` | termine la session |

Le token est envoyé dans l'en-tête `X-Session-Token`. Seul son hash SHA-256 est stocké en base.
Pour protéger une route : `session = Depends(get_current_session)` (401 si absente ou expirée).
Pour limiter l'usage : `verifier_quota_messages(db, session)` ou `verifier_quota_conversations(db, session)` (429 si la limite est atteinte), dans `app/services/quota_service.py`.

Expiration : une session dépassée passe à `expiree` dès sa prochaine utilisation. La purge supprime
les sessions expirées depuis plus de 7 jours avec leurs conversations et messages :

    cd backend
    python -m scripts.purge_sessions     # à planifier régulièrement

Frontend : `frontend/src/lib/session.ts` (`ensureSession`, `sessionFetch`, `endSession`) crée,
réutilise et renouvelle la session ; le token est gardé dans le `localStorage` du navigateur.

Tests : `python -m pytest tests/test_session_service.py tests/test_session_deps.py tests/test_sessions_api.py tests/test_quota_service.py tests/test_session_purge.py`
