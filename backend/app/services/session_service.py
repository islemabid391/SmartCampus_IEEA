"""Gestion des sessions temporaires des visiteurs (sans compte)."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.utilisateur import SessionVisiteur


def generer_token() -> str:
    """Token aléatoire imprévisible (≈ 43 caractères), donné au visiteur une seule fois."""
    return secrets.token_urlsafe(32)


def hasher_token(token: str) -> str:
    """SHA-256 hexadécimal (64 caractères) : seule cette valeur est stockée en base."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def creer_session(db: Session) -> tuple[SessionVisiteur, str]:
    """Crée une session temporaire active.

    Retourne (session, token_en_clair). Le token en clair n'est jamais stocké :
    il doit être renvoyé au visiteur maintenant, on ne pourra plus le retrouver.
    """
    token = generer_token()
    session = SessionVisiteur(
        token_hash=hasher_token(token),
        statut="active",
        date_expiration=datetime.now(timezone.utc)
        + timedelta(minutes=settings.session_ttl_minutes),
    )
    try:
        db.add(session)
        db.commit()
        db.refresh(session)
    except Exception:
        db.rollback()
        raise
    return session, token


def get_session_valide(db: Session, token: str) -> SessionVisiteur | None:
    """Retourne la session si le token est connu et non expiré, sinon None.

    Expiration automatique : si la date est dépassée, la session passe à
    'expiree' en base (une seule fois) et on retourne None.
    """
    session = db.scalar(
        select(SessionVisiteur).where(SessionVisiteur.token_hash == hasher_token(token))
    )
    if session is None:
        return None
    if session.statut == "expiree":
        return None
    if session.date_expiration <= datetime.now(timezone.utc):
        session.statut = "expiree"
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        return None
    return session