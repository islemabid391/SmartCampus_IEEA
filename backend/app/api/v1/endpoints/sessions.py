from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_db
from app.models.utilisateur import SessionVisiteur
from app.schemas.session_visiteur import SessionCreateResponse, SessionStatusResponse
from app.services.quota_service import conversations_restantes, messages_restants
from app.services.session_service import creer_session

router = APIRouter(prefix="/sessions", tags=["Sessions visiteurs"])


def _secondes_restantes(session: SessionVisiteur) -> int:
    reste = (session.date_expiration - datetime.now(timezone.utc)).total_seconds()
    return max(0, int(reste))


@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="CrÃ©er une session visiteur (sans compte)",
)
def create_session(db: Session = Depends(get_db)):
    """Le token n'est renvoyÃ© qu'une seule fois : le client doit le conserver
    et l'envoyer ensuite dans l'en-tÃªte X-Session-Token."""
    session, token = creer_session(db)
    return SessionCreateResponse(
        token=token,
        date_expiration=session.date_expiration,
        expire_dans_secondes=_secondes_restantes(session),
    )


@router.get(
    "/me",
    response_model=SessionStatusResponse,
    summary="Consulter l'Ã©tat de ma session",
)
def read_my_session(
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return SessionStatusResponse(
        statut=session.statut,
        date_creation=session.date_creation,
        date_expiration=session.date_expiration,
        expire_dans_secondes=_secondes_restantes(session),
        messages_restants=messages_restants(db, session),
        conversations_restantes=conversations_restantes(db, session),
    )


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Terminer ma session",
)
def end_my_session(
    session: SessionVisiteur = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    session.statut = "expiree"
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)