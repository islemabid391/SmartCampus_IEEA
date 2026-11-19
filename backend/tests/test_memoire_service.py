from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.memoire_service import (
    ajouter_message,
    creer_conversation,
    get_conversation_de_session,
    get_historique,
    historique_pour_llm,
)
from app.services.session_service import creer_session


@pytest.fixture
def contexte(db_session):
    session, _ = creer_session(db_session)
    conversation = creer_conversation(db_session, session, langue="fr")
    return session, conversation


def test_message_expire_au_plus_tard_avec_la_session(db_session, contexte):
    session, conversation = contexte
    message = ajouter_message(db_session, session, conversation, "user", "Bonjour")
    assert message.date_expiration is not None
    assert message.date_expiration <= session.date_expiration


def test_message_tronque_et_vide_refuse(db_session, contexte, monkeypatch):
    session, conversation = contexte
    monkeypatch.setattr(settings, "memoire_max_caracteres", 10)
    message = ajouter_message(db_session, session, conversation, "user", "a" * 50)
    assert len(message.contenu) == 10
    with pytest.raises(ValueError):
        ajouter_message(db_session, session, conversation, "user", "   ")


def test_historique_ordre_et_fenetre(db_session, contexte):
    session, conversation = contexte
    for i in range(5):
        ajouter_message(db_session, session, conversation, "user", f"question {i}")

    historique = get_historique(db_session, conversation, limite=3)
    assert [m.contenu for m in historique] == ["question 2", "question 3", "question 4"]
    assert historique_pour_llm(historique)[0] == {"role": "user", "content": "question 2"}


def test_historique_ignore_les_messages_expires(db_session, contexte):
    session, conversation = contexte
    vieux = ajouter_message(db_session, session, conversation, "user", "ancien")
    ajouter_message(db_session, session, conversation, "user", "recent")
    vieux.date_expiration = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    assert [m.contenu for m in get_historique(db_session, conversation)] == ["recent"]


def test_stockage_limite_supprime_les_plus_anciens(db_session, contexte, monkeypatch):
    session, conversation = contexte
    monkeypatch.setattr(settings, "memoire_max_messages_stockes", 3)
    for i in range(5):
        ajouter_message(db_session, session, conversation, "assistant", f"reponse {i}")

    contenus = [m.contenu for m in get_historique(db_session, conversation, limite=50)]
    assert contenus == ["reponse 2", "reponse 3", "reponse 4"]


def test_quota_messages_applique_aux_messages_visiteur(db_session, contexte, monkeypatch):
    session, conversation = contexte
    monkeypatch.setattr(settings, "session_max_messages", 1)
    ajouter_message(db_session, session, conversation, "user", "premier")
    ajouter_message(db_session, session, conversation, "assistant", "réponse")  # non compté
    with pytest.raises(HTTPException) as erreur:
        ajouter_message(db_session, session, conversation, "user", "deuxième")
    assert erreur.value.status_code == 429


def test_conversation_appartient_a_sa_session(db_session, contexte):
    session, conversation = contexte
    autre_session, _ = creer_session(db_session)
    assert get_conversation_de_session(db_session, session, conversation.id) is not None
    assert get_conversation_de_session(db_session, autre_session, conversation.id) is None

# ---------- Informations utiles retenues (colonne conversation.memoire) ----------
from app.models.utilisateur import Message  # noqa: E402
from app.services.memoire_service import (  # noqa: E402
    CHAMPS_PROFIL,
    effacer_memoire,
    get_memoire,
    infos_manquantes,
    mettre_a_jour_memoire,
)


def test_memoire_nettoie_les_infos(db_session, contexte):
    _, conversation = contexte
    memoire = mettre_a_jour_memoire(
        db_session,
        conversation,
        {
            "niveau_scolaire": "  Bac 2024  ",
            "moyenne": 25,  # hors 0-20 : ignorée
            "champ_inconnu": "x",  # non autorisé : ignoré
            "centres_interet": ["IA", "", 42, "Robotique"],
        },
    )
    assert memoire == {"niveau_scolaire": "Bac 2024", "centres_interet": ["IA", "Robotique"]}


def test_memoire_fusionne_sans_doublon(db_session, contexte):
    _, conversation = contexte
    mettre_a_jour_memoire(db_session, conversation, {"matieres_preferees": ["Maths"], "moyenne": 14})
    memoire = mettre_a_jour_memoire(
        db_session, conversation, {"matieres_preferees": ["maths", "Info"], "moyenne": 15.5}
    )
    assert memoire["matieres_preferees"] == ["Maths", "Info"]  # pas de doublon "maths"
    assert memoire["moyenne"] == 15.5  # la valeur la plus récente remplace l'ancienne


def test_infos_manquantes_diminuent(db_session, contexte):
    _, conversation = contexte
    assert infos_manquantes(conversation) == CHAMPS_PROFIL
    mettre_a_jour_memoire(db_session, conversation, {"section_bac": "Maths", "moyenne": 13})
    manquantes = infos_manquantes(conversation)
    assert "section_bac" not in manquantes and "moyenne" not in manquantes
    assert "objectif_professionnel" in manquantes


def test_effacer_memoire(db_session, contexte):
    session, conversation = contexte
    ajouter_message(db_session, session, conversation, "user", "Bonjour")
    mettre_a_jour_memoire(db_session, conversation, {"section_bac": "Maths"})

    effacer_memoire(db_session, conversation)

    assert get_memoire(conversation) == {}
    assert get_historique(db_session, conversation) == []
    assert db_session.query(Message).filter_by(conversation_id=conversation.id).count() == 0
