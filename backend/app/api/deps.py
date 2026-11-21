from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.utilisateur import SessionVisiteur, Utilisateur
from app.services.session_service import get_session_valide
from app.core.roles import Role
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

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

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    erreur = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise ou invalide.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise erreur
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise erreur
    try:
        user = db.get(Utilisateur, int(payload["sub"]))
    except (KeyError, ValueError):
        raise erreur
    if user is None or not user.actif:
        raise erreur
    return user


def require_roles(*roles: str):
    def verificateur(user: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès refusé pour votre rôle.")
        return user
    return verificateur


require_candidat = require_roles(Role.CANDIDAT)
require_responsable = require_roles(Role.RESPONSABLE)