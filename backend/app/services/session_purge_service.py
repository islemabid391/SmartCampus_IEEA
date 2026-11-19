"""Nettoyage automatique des sessions visiteurs et des messages expirés."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.models.utilisateur import Message, SessionVisiteur


def purger_sessions_expirees(db: Session, conserver_jours: int = 7) -> dict[str, int]:
    """1) Supprime les messages dont la date d'expiration est dépassée (mémoire temporaire).
    2) Passe à 'expiree' les sessions actives dont la date est dépassée.
    3) Supprime les sessions expirées depuis plus de `conserver_jours` jours
       (leurs conversations et messages partent avec : ON DELETE CASCADE).

    Les sessions rattachées à un utilisateur (candidat) ne sont jamais supprimées.
    """
    maintenant = datetime.now(timezone.utc)
    limite = maintenant - timedelta(days=conserver_jours)
    try:
        messages_supprimes = db.execute(
            delete(Message).where(
                Message.date_expiration.is_not(None),
                Message.date_expiration <= maintenant,
            )
        ).rowcount
        marquees = db.execute(
            update(SessionVisiteur)
            .where(
                SessionVisiteur.statut == "active",
                SessionVisiteur.date_expiration <= maintenant,
            )
            .values(statut="expiree")
        ).rowcount
        supprimees = db.execute(
            delete(SessionVisiteur).where(
                SessionVisiteur.statut == "expiree",
                SessionVisiteur.utilisateur_id.is_(None),
                SessionVisiteur.date_expiration <= limite,
            )
        ).rowcount
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "messages_supprimes": messages_supprimes,
        "marquees_expirees": marquees,
        "supprimees": supprimees,
    }