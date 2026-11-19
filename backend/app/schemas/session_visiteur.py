from datetime import datetime

from pydantic import BaseModel


class SessionCreateResponse(BaseModel):
    """Réponse à la création : le token n'est affiché qu'ici, une seule fois."""

    token: str
    date_expiration: datetime
    expire_dans_secondes: int


class SessionStatusResponse(BaseModel):
    """État courant d'une session (sans jamais renvoyer le token)."""

    statut: str
    date_creation: datetime
    date_expiration: datetime
    expire_dans_secondes: int
    messages_restants: int
    conversations_restantes: int