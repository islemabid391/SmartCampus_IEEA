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

## Lancement avec Docker (recommandé)
1. Copier backend/.env.example en backend/.env
2. Copier frontend/.env.example en frontend/.env.local
3. Depuis la racine : docker compose up --build

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