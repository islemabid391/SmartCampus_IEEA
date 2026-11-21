from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.models.utilisateur import Utilisateur
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import authentifier, creer_candidat

router = APIRouter(prefix="/auth", tags=["Authentification"])


def _token_response(user: Utilisateur) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
             summary="Créer un compte candidat")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = creer_candidat(db, data)
    except LookupError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    return _token_response(user)  # connexion directe après inscription


@router.post("/login", response_model=TokenResponse, summary="Se connecter")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authentifier(db, data.email, data.mot_de_passe)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(user)


@router.get("/me", response_model=UserResponse, summary="Mon profil utilisateur")
def me(user: Utilisateur = Depends(get_current_user)):
    return user