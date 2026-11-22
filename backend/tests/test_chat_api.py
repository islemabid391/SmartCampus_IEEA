import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.core.prompts import SYSTEM_PROMPT
from app.models.utilisateur import Conversation, Message
from app.services.memoire_service import mettre_a_jour_memoire
from app.core.config import settings
from app.services import llm_service
from app.services.llm_service import LLMReponse, LLMTimeout


@pytest.fixture
def entetes(client):
    token = client.post("/api/v1/sessions").json()["token"]
    return {"X-Session-Token": token}


@pytest.fixture
def conversation_id(client, entetes):
    return client.post("/api/v1/conversations", headers=entetes).json()["id"]


@pytest.fixture
def llm_simule(monkeypatch):
    """Remplace l'appel au vrai LLM : aucune clé ni réseau nécessaires."""
    appels = []

    def faux(messages, http_client=None):
        appels.append(messages)
        return LLMReponse("Voici la réponse.", "modele-test", "stop", 10, 5, 42)

    monkeypatch.setattr(llm_service, "appeler_llm", faux)
    return appels


def url(cid):
    return f"/api/v1/conversations/{cid}/chat"


def test_sans_session_401(client, conversation_id):
    assert client.post(url(conversation_id), json={"contenu": "Bonjour"}).status_code == 401


def test_conversation_inconnue_ou_d_une_autre_session_404(client, entetes, conversation_id, llm_simule):
    assert client.post(url(999999), json={"contenu": "Bonjour"}, headers=entetes).status_code == 404
    autre = {"X-Session-Token": client.post("/api/v1/sessions").json()["token"]}
    assert client.post(url(conversation_id), json={"contenu": "Bonjour"}, headers=autre).status_code == 404
    assert llm_simule == []  # le LLM n'est jamais appelé


def test_question_reponse_enregistrees(client, entetes, conversation_id, llm_simule):
    r = client.post(url(conversation_id), json={"contenu": "Quels sont les frais ?"}, headers=entetes)

    assert r.status_code == 200
    corps = r.json()
    assert corps["reponse"]["role"] == "assistant"
    assert corps["reponse"]["contenu"] == "Voici la réponse."
    assert (corps["modele"], corps["duree_ms"], corps["tronquee"]) == ("modele-test", 42, False)

    historique = client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=entetes).json()
    assert [(m["role"], m["contenu"]) for m in historique] == [
        ("user", "Quels sont les frais ?"),
        ("assistant", "Voici la réponse."),
    ]

def test_dialogue_multi_tours_le_modele_recoit_l_historique(client, entetes, conversation_id, llm_simule):
    client.post(url(conversation_id), json={"contenu": "Je suis en Bac Maths"}, headers=entetes)
    client.post(url(conversation_id), json={"contenu": "Et pour l'informatique ?"}, headers=entetes)

    second_envoi = llm_simule[1]
    assert [m["role"] for m in second_envoi] == ["system", "user", "assistant", "user"]
    assert second_envoi[1]["content"] == "Je suis en Bac Maths"
    assert second_envoi[-1]["content"] == "Et pour l'informatique ?"


def test_erreur_du_llm_renvoyee_sans_rien_enregistrer(client, entetes, conversation_id, monkeypatch):
    def en_panne(messages, http_client=None):
        raise LLMTimeout()

    monkeypatch.setattr(llm_service, "appeler_llm", en_panne)
    r = client.post(url(conversation_id), json={"contenu": "Bonjour"}, headers=entetes)

    assert r.status_code == 504
    assert r.json()["detail"] == LLMTimeout.message_par_defaut
    historique = client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=entetes).json()
    assert historique == []  # on peut renvoyer la même question


def test_quota_de_messages_atteint_429_sans_appel_au_llm(client, entetes, conversation_id, llm_simule, monkeypatch):
    monkeypatch.setattr(settings, "session_max_messages", 1)
    assert client.post(url(conversation_id), json={"contenu": "Un"}, headers=entetes).status_code == 200
    r = client.post(url(conversation_id), json={"contenu": "Deux"}, headers=entetes)

    assert r.status_code == 429
    assert len(llm_simule) == 1


def test_message_vide_refuse(client, entetes, conversation_id, llm_simule):
    assert client.post(url(conversation_id), json={"contenu": "   "}, headers=entetes).status_code == 422
    assert llm_simule == []
    
def test_la_fenetre_de_contexte_limite_l_historique(
    client, entetes, conversation_id, llm_simule, monkeypatch
):
    monkeypatch.setattr(settings, "memoire_fenetre_messages", 4)
    for numero in range(1, 5):
        r = client.post(url(conversation_id), json={"contenu": f"Question {numero}"}, headers=entetes)
        assert r.status_code == 200

    quatrieme_envoi = llm_simule[3]
    questions = [m["content"] for m in quatrieme_envoi if m["role"] == "user"]
    assert questions == ["Question 2", "Question 3", "Question 4"]  # la question 1 est sortie de la fenêtre


def test_un_message_expire_n_est_plus_envoye_au_modele(
    client, db_session, entetes, conversation_id, llm_simule
):
    client.post(url(conversation_id), json={"contenu": "Question ancienne"}, headers=entetes)
    db_session.execute(
        update(Message)
        .where(Message.conversation_id == conversation_id)
        .values(date_expiration=datetime.now(timezone.utc) - timedelta(minutes=1))
    )
    db_session.flush()

    client.post(url(conversation_id), json={"contenu": "Nouvelle question"}, headers=entetes)
    assert [m["role"] for m in llm_simule[1]] == ["system", "user"]


def test_les_informations_deja_connues_sont_transmises(
    client, db_session, entetes, conversation_id, llm_simule
):
    conversation = db_session.get(Conversation, conversation_id)
    mettre_a_jour_memoire(
        db_session, conversation,
        {"niveau_scolaire": "Terminale", "centres_interet": ["maths"]},
    )
    client.post(url(conversation_id), json={"contenu": "Que me conseillez-vous ?"}, headers=entetes)

    systeme = llm_simule[0][0]["content"]
    assert "Niveau scolaire : Terminale" in systeme
    assert "Centres d'intérêt : maths" in systeme


def test_les_regles_sur_les_informations_officielles_sont_envoyees(
    client, entetes, conversation_id, llm_simule
):
    client.post(url(conversation_id), json={"contenu": "C'est combien ?"}, headers=entetes)
    assert SYSTEM_PROMPT in llm_simule[0][0]["content"]    