from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.utilisateur import SessionVisiteur
from app.services.session_service import get_session_valide


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_session(
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> SessionVisiteur:
    """Session visiteur courante, lue dans l'en-tête HTTP X-Session-Token.

    401 si le token est absent, inconnu ou expiré.
    """
    if not x_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session manquante. Créez une session avec POST /api/v1/sessions.",
        )
    session = get_session_valide(db, x_session_token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide ou expirée.",
        )
    return session