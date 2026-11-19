def test_creer_puis_consulter_session(client):
    r = client.post("/api/v1/sessions")
    assert r.status_code == 201
    data = r.json()
    assert data["token"]
    assert data["expire_dans_secondes"] > 0

    h = {"X-Session-Token": data["token"]}
    r = client.get("/api/v1/sessions/me", headers=h)
    assert r.status_code == 200
    assert r.json()["statut"] == "active"
    assert "token" not in r.json()  # le token n'est jamais renvoyé ici


def test_consulter_sans_token_401(client):
    assert client.get("/api/v1/sessions/me").status_code == 401


def test_terminer_session(client):
    token = client.post("/api/v1/sessions").json()["token"]
    h = {"X-Session-Token": token}

    assert client.delete("/api/v1/sessions/me", headers=h).status_code == 204
    # une fois terminée, la session n'est plus utilisable
    assert client.get("/api/v1/sessions/me", headers=h).status_code == 401

def test_status_indique_les_quotas_restants(client):
    from app.core.config import settings

    token = client.post("/api/v1/sessions").json()["token"]
    data = client.get("/api/v1/sessions/me", headers={"X-Session-Token": token}).json()
    assert data["messages_restants"] == settings.session_max_messages
    assert data["conversations_restantes"] == settings.session_max_conversations
