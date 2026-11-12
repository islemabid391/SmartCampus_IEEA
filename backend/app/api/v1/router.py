from fastapi import APIRouter

from app.api.v1.endpoints import health
# Pour ajouter un module : créer un fichier dans endpoints/,
# l'importer ici, puis ajouter une ligne include_router.

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])