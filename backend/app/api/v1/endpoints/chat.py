"""Envoi d'une question à l'assistant (LLM) dans une conversation."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_db, require_candidat
from app.core.config import settings
from app.models.utilisateur import Conversation, SessionVisiteur, Utilisateur
from app.schemas.conversation import ChatRequest, ChatResponse
from app.services import llm_service
from app.services.chat_service import repondre
from app.services.memoire_service import get_conversation_de_session
from app.services.quota_service import verifier_quota_candidat

router = APIRouter(prefix="/conversations", tags=["Chat (LLM)"])
router_candidat = APIRouter(prefix="/me/conversations", tags=["Chat (LLM)"])


def _question(data: ChatRequest) -> str:
    question = data.contenu.strip()[: settings.memoire_max_caracteres]
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Le message est vide.")
    return question


def _repondre(db, conversation, data, session=None) -> ChatResponse:
    """Appelle le LLM ; une erreur du LLM devient une erreur HTTP sans détail technique."""
    try:
        reponse, resultat = repondre(db, conversation, _question(data), data.langue, session)
    except llm_service.LLMError as erreur:
        raise HTTPException(erreur.status_code, erreur.message)
    return ChatResponse(
        reponse=reponse,
        modele=resultat.modele,
        duree_ms=resultat.duree_ms,
        tronquee=resultat.tronquee,
    )

@router.post(
    "/{conversation_id}/chat",
    response_model=ChatResponse,
    summary="Poser une question à l'assistant (visiteur)",
)
def chat(
    data: ChatRequest,
    conversation_id: int = Path(gt=0),
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    """Visiteur avec session.

    - 401 session invalide, 404 conversation inconnue, 429 quota de messages atteint ;
    - 503 / 504 / 502 si le service d'IA est indisponible, trop lent ou renvoie une erreur ;
    - la question et la réponse ne sont enregistrées qu'en cas de succès : en cas d'erreur,
      le visiteur peut renvoyer la même question sans doublon ni quota consommé.
    """
    conversation = get_conversation_de_session(db, session, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable.")
    return _repondre(db, conversation, data, session)


@router_candidat.post(
    "/{conversation_id}/chat",
    response_model=ChatResponse,
    summary="Continuer une de mes conversations avec l'assistant (candidat connecté)",
)
def chat_candidat(
    data: ChatRequest,
    conversation_id: int = Path(gt=0),
    utilisateur: Utilisateur = Depends(require_candidat),
    db: Session = Depends(get_db),
):
    """Candidat connecté : chaque conversation garde son propre contexte et sa propre mémoire.

    404 si la conversation n'est pas la sienne ; 429 si la limite quotidienne est atteinte.
    """
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.utilisateur_id == utilisateur.id,  # jamais celle d'un autre
        )
    )
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable.")
    verifier_quota_candidat(db, utilisateur.id)
    return _repondre(db, conversation, data)