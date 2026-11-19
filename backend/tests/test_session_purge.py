from datetime import timedelta, datetime, timezone

from sqlalchemy import select

from app.models.utilisateur import Conversation, SessionVisiteur
from app.services.session_purge_service import purger_sessions_expirees
from app.services.session_service import creer_session


def _session(db, statut, decalage):
    """Crée une session avec un statut et une date d'expiration décalée de `decalage`."""
    session, _ = creer_session(db)
    session.statut = statut
    session.date_expiration = datetime.now(timezone.utc) + decalage
    db.commit()
    return session.id


def _statut(db, session_id):
    db.expunge_all()
    return db.scalar(select(SessionVisiteur.statut).where(SessionVisiteur.id == session_id))


def test_purge_marque_les_sessions_expirees(db_session):
    valide = _session(db_session, "active", timedelta(hours=1))
    perimee = _session(db_session, "active", timedelta(minutes=-1))

    purger_sessions_expirees(db_session)

    assert _statut(db_session, valide) == "active"
    assert _statut(db_session, perimee) == "expiree"


def test_purge_supprime_les_anciennes_et_leurs_conversations(db_session):
    ancienne = _session(db_session, "expiree", timedelta(days=-10))
    recente = _session(db_session, "expiree", timedelta(days=-1))
    db_session.add(Conversation(session_id=ancienne))
    db_session.commit()

    resultat = purger_sessions_expirees(db_session, conserver_jours=7)

    assert resultat["supprimees"] >= 1
    assert _statut(db_session, ancienne) is None  # supprimée
    assert _statut(db_session, recente) == "expiree"  # conservée 7 jours
    restantes = db_session.scalar(
        select(Conversation.id).where(Conversation.session_id == ancienne)
    )
    assert restantes is None  # conversation supprimée en cascade

def test_purge_supprime_les_messages_expires_mais_garde_les_valides(db_session):
    from app.models.utilisateur import Message

    session_id = _session(db_session, "active", timedelta(hours=1))
    conversation = Conversation(session_id=session_id)
    db_session.add(conversation)
    db_session.flush()
    maintenant = datetime.now(timezone.utc)
    expire = Message(
        conversation_id=conversation.id, role="user", contenu="expiré",
        date_expiration=maintenant - timedelta(minutes=1),
    )
    valide = Message(
        conversation_id=conversation.id, role="user", contenu="valide",
        date_expiration=maintenant + timedelta(minutes=30),
    )
    db_session.add_all([expire, valide])
    db_session.commit()
    expire_id, valide_id = expire.id, valide.id

    resultat = purger_sessions_expirees(db_session)

    assert resultat["messages_supprimes"] >= 1
    db_session.expunge_all()
    assert db_session.get(Message, expire_id) is None
    assert db_session.get(Message, valide_id) is not None
    assert _statut(db_session, session_id) == "active"  # la session, elle, reste active
