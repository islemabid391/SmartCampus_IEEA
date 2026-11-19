import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.utilisateur import Conversation, Message
from app.services.quota_service import (
    compter_conversations,
    compter_messages,
    conversations_restantes,
    messages_restants,
    verifier_quota_conversations,
    verifier_quota_messages,
)
from app.services.session_service import creer_session


def _conversation_avec_messages(db, session, nb_user, nb_assistant=0):
    conv = Conversation(session_id=session.id)
    db.add(conv)
    db.flush()
    for i in range(nb_user):
        db.add(Message(conversation_id=conv.id, role="user", contenu=f"question {i}"))
    for i in range(nb_assistant):
        db.add(Message(conversation_id=conv.id, role="assistant", contenu=f"réponse {i}"))
    db.flush()
    return conv


def test_quota_messages(db_session, monkeypatch):
    monkeypatch.setattr(settings, "session_max_messages", 2)
    session, _ = creer_session(db_session)

    assert messages_restants(db_session, session) == 2
    verifier_quota_messages(db_session, session)  # pas d'erreur

    # 2 messages visiteur + 3 réponses de l'assistant : seuls les "user" comptent
    _conversation_avec_messages(db_session, session, nb_user=2, nb_assistant=3)
    assert compter_messages(db_session, session) == 2
    assert messages_restants(db_session, session) == 0

    with pytest.raises(HTTPException) as erreur:
        verifier_quota_messages(db_session, session)
    assert erreur.value.status_code == 429


def test_quota_conversations(db_session, monkeypatch):
    monkeypatch.setattr(settings, "session_max_conversations", 1)
    session, _ = creer_session(db_session)

    assert conversations_restantes(db_session, session) == 1
    verifier_quota_conversations(db_session, session)  # pas d'erreur

    _conversation_avec_messages(db_session, session, nb_user=0)
    assert compter_conversations(db_session, session) == 1

    with pytest.raises(HTTPException) as erreur:
        verifier_quota_conversations(db_session, session)
    assert erreur.value.status_code == 429


def test_quota_independant_entre_sessions(db_session, monkeypatch):
    monkeypatch.setattr(settings, "session_max_messages", 1)
    session_a, _ = creer_session(db_session)
    session_b, _ = creer_session(db_session)

    _conversation_avec_messages(db_session, session_a, nb_user=1)
    assert messages_restants(db_session, session_a) == 0
    assert messages_restants(db_session, session_b) == 1