import pytest

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

# --- Candidat connecté : chaque conversation continue séparément ---

URL_RATTACHEMENT = "/api/v1/sessions/me/rattachement"


def _candidat_avec_conversation_rattachee(client, email):
    """Visiteur avec une conversation, puis connexion et rattachement au compte."""
    token = client.post("/api/v1/sessions").json()["token"]
    visiteur = {"X-Session-Token": token}
    cid = client.post("/api/v1/conversations", headers=visiteur).json()["id"]
    client.post(f"/api/v1/conversations/{cid}/messages", json={"contenu": "Bonjour"}, headers=visiteur)
    r = client.post("/api/v1/auth/register", json={
        "email": email, "mot_de_passe": "MotDePasse123",
        "nom": "Test", "prenom": "Candidat", "consentement_rgpd": True,
    })
    compte = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.post(URL_RATTACHEMENT, json={"consentement": True}, headers={**visiteur, **compte}).status_code == 200
    return compte, visiteur, cid


def url_candidat(cid):
    return f"/api/v1/me/conversations/{cid}/chat"


def test_candidat_continue_sa_conversation_rattachee(client, llm_simule):
    compte, _, cid = _candidat_avec_conversation_rattachee(client, "chat.candidat1@example.com")

    r = client.post(url_candidat(cid), json={"contenu": "Et les frais ?"}, headers=compte)

    assert r.status_code == 200
    assert r.json()["reponse"]["date_expiration"] is None  # message permanent
    assert [m["role"] for m in llm_simule[0]] == ["system", "user", "user"]  # "Bonjour" + question
    messages = client.get(f"/api/v1/me/conversations/{cid}/messages", headers=compte).json()
    assert [m["role"] for m in messages] == ["user", "user", "assistant"]

def test_candidat_ne_peut_pas_ecrire_dans_la_conversation_d_un_autre(client, llm_simule):
    _, _, cid = _candidat_avec_conversation_rattachee(client, "chat.candidat2@example.com")
    r = client.post("/api/v1/auth/register", json={
        "email": "chat.candidat3@example.com", "mot_de_passe": "MotDePasse123",
        "nom": "Autre", "prenom": "Candidat", "consentement_rgpd": True,
    })
    autre = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert client.post(url_candidat(cid), json={"contenu": "Salut"}, headers=autre).status_code == 404
    assert llm_simule == []


def test_candidat_sans_jwt_401(client, llm_simule):
    assert client.post(url_candidat(1), json={"contenu": "Salut"}).status_code == 401


def test_candidat_limite_quotidienne_429(client, llm_simule, monkeypatch):
    compte, _, cid = _candidat_avec_conversation_rattachee(client, "chat.candidat4@example.com")
    monkeypatch.setattr(settings, "candidat_max_messages_jour", 1)  # "Bonjour" compte déjà pour 1

    r = client.post(url_candidat(cid), json={"contenu": "Encore"}, headers=compte)
    assert r.status_code == 429
    assert llm_simule == []


def test_ancien_chat_visiteur_ne_marche_plus_apres_rattachement(client, llm_simule):
    _, visiteur, cid = _candidat_avec_conversation_rattachee(client, "chat.candidat5@example.com")
    # la session visiteur est « rattachée » : son ancien token est mort (401)
    assert client.post(url(cid), json={"contenu": "Salut"}, headers=visiteur).status_code == 401