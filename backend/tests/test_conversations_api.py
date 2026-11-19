import pytest

from app.core.config import settings


@pytest.fixture
def entetes(client):
    token = client.post("/api/v1/sessions").json()["token"]
    return {"X-Session-Token": token}


def test_sans_session_401(client):
    assert client.post("/api/v1/conversations").status_code == 401


def test_conversation_messages_et_historique(client, entetes):
    conv = client.post("/api/v1/conversations?langue=fr", headers=entetes)
    assert conv.status_code == 201
    cid = conv.json()["id"]

    for texte in ["Bonjour", "J'aime les maths"]:
        r = client.post(
            f"/api/v1/conversations/{cid}/messages", json={"contenu": texte}, headers=entetes
        )
        assert r.status_code == 201
        assert r.json()["role"] == "user"
        assert r.json()["date_expiration"] is not None

    historique = client.get(f"/api/v1/conversations/{cid}/messages", headers=entetes).json()
    assert [m["contenu"] for m in historique] == ["Bonjour", "J'aime les maths"]


def test_message_vide_refuse(client, entetes):
    cid = client.post("/api/v1/conversations", headers=entetes).json()["id"]
    r = client.post(
        f"/api/v1/conversations/{cid}/messages", json={"contenu": "   "}, headers=entetes
    )
    assert r.status_code == 422


def test_memoire_vide_puis_oubli(client, entetes):
    cid = client.post("/api/v1/conversations", headers=entetes).json()["id"]
    client.post(
        f"/api/v1/conversations/{cid}/messages", json={"contenu": "Bonjour"}, headers=entetes
    )

    memoire = client.get(f"/api/v1/conversations/{cid}/memoire", headers=entetes).json()
    assert memoire["informations"] == {}
    assert "niveau_scolaire" in memoire["infos_manquantes"]

    assert client.delete(f"/api/v1/conversations/{cid}/memoire", headers=entetes).status_code == 204
    assert client.get(f"/api/v1/conversations/{cid}/messages", headers=entetes).json() == []


def test_conversation_d_une_autre_session_404(client, entetes):
    cid = client.post("/api/v1/conversations", headers=entetes).json()["id"]
    autre = {"X-Session-Token": client.post("/api/v1/sessions").json()["token"]}

    assert client.get(f"/api/v1/conversations/{cid}/messages", headers=autre).status_code == 404
    assert client.get(f"/api/v1/conversations/{cid}/memoire", headers=autre).status_code == 404
    r = client.post(
        f"/api/v1/conversations/{cid}/messages", json={"contenu": "intrus"}, headers=autre
    )
    assert r.status_code == 404


def test_quotas_429(client, entetes, monkeypatch):
    monkeypatch.setattr(settings, "session_max_conversations", 1)
    monkeypatch.setattr(settings, "session_max_messages", 1)

    cid = client.post("/api/v1/conversations", headers=entetes).json()["id"]
    assert client.post("/api/v1/conversations", headers=entetes).status_code == 429

    url = f"/api/v1/conversations/{cid}/messages"
    assert client.post(url, json={"contenu": "un"}, headers=entetes).status_code == 201
    assert client.post(url, json={"contenu": "deux"}, headers=entetes).status_code == 429