from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_candidat
from app.models.utilisateur import Conversation, Message, Utilisateur
from app.schemas.conversation import ConversationResponse, MessageResponse

router = APIRouter(prefix="/me/conversations", tags=["Mes conversations (candidat)"])


@router.get(
    "",
    response_model=list[ConversationResponse],
    summary="Lister mes conversations",
)
def mes_conversations(
    utilisateur: Utilisateur = Depends(require_candidat),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.utilisateur_id == utilisateur.id)
            .order_by(Conversation.id)
        )
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Lire les messages d'une de mes conversations",
)
def mes_messages(
    conversation_id: int = Path(gt=0),
    utilisateur: Utilisateur = Depends(require_candidat),
    db: Session = Depends(get_db),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.utilisateur_id == utilisateur.id,  # jamais celle d'un autre
        )
    )
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable.")
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.id)
        )
    )