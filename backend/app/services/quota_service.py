"""Limites d'utilisation d'une session visiteur (anti-abus)."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.utilisateur import Conversation, Message, SessionVisiteur


def compter_messages(db: Session, session: SessionVisiteur) -> int:
    """Nombre de messages envoyés par le visiteur (role 'user') dans cette session."""
    return db.scalar(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.session_id == session.id, Message.role == "user")
    ) or 0


def compter_conversations(db: Session, session: SessionVisiteur) -> int:
    return db.scalar(
        select(func.count(Conversation.id)).where(Conversation.session_id == session.id)
    ) or 0


def messages_restants(db: Session, session: SessionVisiteur) -> int:
    return max(0, settings.session_max_messages - compter_messages(db, session))


def conversations_restantes(db: Session, session: SessionVisiteur) -> int:
    return max(0, settings.session_max_conversations - compter_conversations(db, session))


def verifier_quota_messages(db: Session, session: SessionVisiteur) -> None:
    """À appeler avant d'accepter un nouveau message. 429 si la limite est atteinte."""
    if messages_restants(db, session) == 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de messages atteinte pour cette session. "
            "Créez un compte ou une préinscription pour continuer.",
        )


def verifier_quota_conversations(db: Session, session: SessionVisiteur) -> None:
    """À appeler avant de créer une conversation. 429 si la limite est atteinte."""
    if conversations_restantes(db, session) == 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de conversations atteinte pour cette session.",
        )

def verifier_quota_candidat(db: Session, utilisateur_id: int) -> None:
    """Limite quotidienne d'un candidat connecté (protège le quota du LLM). 429 si atteinte."""
    depuis = datetime.now(timezone.utc) - timedelta(days=1)
    envoyes = db.scalar(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.utilisateur_id == utilisateur_id,
            Message.role == "user",
            Message.date_creation >= depuis,
        )
    ) or 0
    if envoyes >= settings.candidat_max_messages_jour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite quotidienne de messages atteinte. Réessayez demain.",
        )