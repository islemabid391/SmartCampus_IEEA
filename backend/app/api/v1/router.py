
from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    tarifs,
    conditions_admission,
    sessions,
    conversations,
)


api_router = APIRouter()

# Health check
api_router.include_router(
    health.router,
    tags=["health"]
)

# Gestion et consultation des tarifs
api_router.include_router(
    tarifs.router
)

# Gestion et consultation des conditions d'admission
api_router.include_router(
    conditions_admission.router
)


# from fastapi import APIRouter

# from app.api.v1.endpoints import health
# # Pour ajouter un module : crÃƒÂ©er un fichier dans endpoints/,
# # l'importer ici, puis ajouter une ligne include_router.

# api_router = APIRouter()
# api_router.include_router(health.router, tags=["health"])

# Sessions visiteurs (conversation sans compte)
api_router.include_router(sessions.router)

# Conversations et mémoire temporaire
api_router.include_router(conversations.router)
