from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_db, require_candidat
from app.models.utilisateur import SessionVisiteur, Utilisateur
from app.schemas.rattachement import (
    RattachementApercu,
    RattachementRequest,
    RattachementResponse,
)
from app.services.rattachement_service import (
    ConsentementRequis,
    RattachementImpossible,
    apercu_rattachement,
    rattacher_session,
)

router = APIRouter(
    prefix="/sessions/me/rattachement",
    tags=["Rattachement de session"],
)


@router.get(
    "",
    response_model=RattachementApercu,
    summary="Proposer le rattachement : que contient ma session ?",
)
def lire_apercu(
    session: SessionVisiteur = Depends(get_current_session),  # preuve : la session est à moi
    utilisateur: Utilisateur = Depends(require_candidat),     # je suis identifié
    db: Session = Depends(get_db),
):
    return apercu_rattachement(db, session)


@router.post(
    "",
    response_model=RattachementResponse,
    summary="Rattacher ma session visiteur à mon compte (avec consentement)",
)
def rattacher(
    data: RattachementRequest,
    session: SessionVisiteur = Depends(get_current_session),
    utilisateur: Utilisateur = Depends(require_candidat),
    db: Session = Depends(get_db),
):
    try:
        nombre = rattacher_session(db, session, utilisateur, data.consentement)
    except ConsentementRequis as erreur:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(erreur))
    except RattachementImpossible as erreur:
        raise HTTPException(status.HTTP_409_CONFLICT, str(erreur))
    return RattachementResponse(conversations_rattachees=nombre)