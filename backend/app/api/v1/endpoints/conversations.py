from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_db
from app.core.config import settings
from app.models.utilisateur import Conversation, SessionVisiteur
from app.schemas.conversation import (
    ConversationResponse,
    MemoireResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.memoire_service import (
    ajouter_message,
    creer_conversation,
    effacer_memoire,
    get_conversation_de_session,
    get_historique,
    get_memoire,
    infos_manquantes,
)

router = APIRouter(prefix="/conversations", tags=["Conversations (mémoire temporaire)"])


def _conversation_ou_404(
    db: Session, session: SessionVisiteur, conversation_id: int
) -> Conversation:
    conversation = get_conversation_de_session(db, session, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable.")
    return conversation


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ouvrir une conversation dans ma session",
)
def create_conversation(
    langue: str | None = Query(default=None, max_length=20),
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    """429 si la limite de conversations de la session est atteinte."""
    return creer_conversation(db, session, langue=langue)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer un message du visiteur",
)
def add_message(
    data: MessageCreate,
    conversation_id: int = Path(gt=0),
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    """Enregistre le message (rôle 'user'). 429 si le quota de messages est atteint.
    La réponse de l'agent sera enregistrée par le service avec le rôle 'assistant'."""
    conversation = _conversation_ou_404(db, session, conversation_id)
    try:
        return ajouter_message(
            db, session, conversation, "user", data.contenu, langue=data.langue
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Derniers messages non expirés de la conversation",
)
def read_messages(
    conversation_id: int = Path(gt=0),
    limite: int = Query(default=settings.memoire_fenetre_messages, ge=1, le=100),
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    conversation = _conversation_ou_404(db, session, conversation_id)
    return get_historique(db, conversation, limite=limite)


@router.get(
    "/{conversation_id}/memoire",
    response_model=MemoireResponse,
    summary="Informations retenues sur le visiteur",
)
def read_memoire(
    conversation_id: int = Path(gt=0),
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    conversation = _conversation_ou_404(db, session, conversation_id)
    return MemoireResponse(
        informations=get_memoire(conversation),
        infos_manquantes=infos_manquantes(conversation),
    )


@router.delete(
    "/{conversation_id}/memoire",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Oublier : supprimer les messages et les informations retenues",
)
def forget_conversation(
    conversation_id: int = Path(gt=0),
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    conversation = _conversation_ou_404(db, session, conversation_id)
    effacer_memoire(db, conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)