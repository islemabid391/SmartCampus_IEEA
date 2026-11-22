"""Envoi d'une question à l'assistant (LLM) dans une conversation."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_db
from app.core.config import settings
from app.models.utilisateur import SessionVisiteur
from app.schemas.conversation import ChatRequest, ChatResponse
from app.services import llm_service
from app.services.chat_service import construire_messages
from app.services.memoire_service import (
    ajouter_message,
    get_conversation_de_session,
    get_historique,
    get_memoire,
)
from app.services.quota_service import verifier_quota_messages

router = APIRouter(prefix="/conversations", tags=["Chat (LLM)"])

@router.post(
    "/{conversation_id}/chat",
    response_model=ChatResponse,
    summary="Poser une question à l'assistant",
)
def chat(
    data: ChatRequest,
    conversation_id: int = Path(gt=0),
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    """Envoie la question au LLM avec l'historique récent et les informations déjà connues.

    - 401 session invalide, 404 conversation inconnue, 429 quota de messages atteint ;
    - 503 / 504 / 502 si le service d'IA est indisponible, trop lent ou renvoie une erreur ;
    - la question et la réponse ne sont enregistrées qu'en cas de succès : en cas d'erreur,
      le visiteur peut renvoyer la même question sans doublon ni quota consommé.
    """
    conversation = get_conversation_de_session(db, session, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable.")

    question = data.contenu.strip()[: settings.memoire_max_caracteres]
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Le message est vide.")
    verifier_quota_messages(db, session)  # avant l'appel (payant) au LLM

    messages = construire_messages(question, get_historique(db, conversation), get_memoire(conversation))
    try:
        resultat = llm_service.appeler_llm(messages)
    except llm_service.LLMError as erreur:
        raise HTTPException(erreur.status_code, erreur.message)

    ajouter_message(db, session, conversation, "user", question, langue=data.langue)
    reponse = ajouter_message(db, session, conversation, "assistant", resultat.texte)
    return ChatResponse(
        reponse=reponse,
        modele=resultat.modele,
        duree_ms=resultat.duree_ms,
        tronquee=resultat.tronquee,
    )