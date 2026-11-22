import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from pydantic import SecretStr


class _FauxLLMHandler(BaseHTTPRequestHandler):
    mode = "ok"
    delai_secondes = 0.0
    appels: list[list[dict[str, str]]] = []

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        longueur = int(self.headers.get("Content-Length", "0"))
        corps = json.loads(self.rfile.read(longueur).decode("utf-8"))
        type(self).appels.append(corps.get("messages", []))

        if type(self).delai_secondes > 0:
            time.sleep(type(self).delai_secondes)

        if type(self).mode == "down":
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": {"message": "Service temporairement indisponible"}}')
            return

        dernier_user = next(
            (m["content"] for m in reversed(corps.get("messages", [])) if m.get("role") == "user"),
            "",
        )
        reponse = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "model": "openai/gpt-oss-20b",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Reponse simulee a : {dernier_user}",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }
        payload = json.dumps(reponse).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture
def faux_llm(monkeypatch):
    _FauxLLMHandler.mode = "ok"
    _FauxLLMHandler.delai_secondes = 0.0
    _FauxLLMHandler.appels = []

    serveur = HTTPServer(("127.0.0.1", 0), _FauxLLMHandler)
    thread = threading.Thread(target=serveur.serve_forever, daemon=True)
    thread.start()

    monkeypatch.setattr(settings, "llm_base_url", f"http://127.0.0.1:{serveur.server_port}/v1")
    monkeypatch.setattr(settings, "llm_api_key", SecretStr("cle-test-factice"))
    monkeypatch.setattr(settings, "llm_max_retries", 0)
    monkeypatch.setattr(settings, "llm_timeout_secondes", 0.3)

    yield _FauxLLMHandler
    serveur.shutdown()
    serveur.server_close()


def _nouvelle_conversation(client: TestClient) -> tuple[str, int]:
    r_sess = client.post("/api/v1/sessions")
    assert r_sess.status_code == 201
    token = r_sess.json()["token"]

    r_conv = client.post(
        "/api/v1/conversations",
        params={"langue": "fr"},
        headers={"x-session-token": token},
    )
    assert r_conv.status_code == 201
    return token, r_conv.json()["id"]


def test_echanges_successifs(faux_llm):
    with TestClient(app) as client:
        token, cid = _nouvelle_conversation(client)
        messages = [
            "Bonjour, je m appelle Salma.",
            "J ai eu 15.5 de moyenne.",
            "Quelle filiere informatique me conseilles-tu ?",
        ]
        for msg in messages:
            res = client.post(
                f"/api/v1/conversations/{cid}/chat",
                headers={"x-session-token": token},
                json={"contenu": msg, "langue": "fr"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["reponse"]["role"] == "assistant"
            assert msg in data["reponse"]["contenu"]


def test_historique_transmis_au_llm(faux_llm):
    with TestClient(app) as client:
        token, cid = _nouvelle_conversation(client)

        r1 = client.post(
            f"/api/v1/conversations/{cid}/chat",
            headers={"x-session-token": token},
            json={"contenu": "Mon prenom est Salma.", "langue": "fr"},
        )
        assert r1.status_code == 200

        r2 = client.post(
            f"/api/v1/conversations/{cid}/chat",
            headers={"x-session-token": token},
            json={"contenu": "Quel est mon prenom ?", "langue": "fr"},
        )
        assert r2.status_code == 200

        assert len(faux_llm.appels) == 2
        contenus_appel_2 = " ".join(m["content"] for m in faux_llm.appels[1])
        assert "Mon prenom est Salma." in contenus_appel_2
        assert "Quel est mon prenom ?" in contenus_appel_2


def test_sessions_isolees(faux_llm):
    with TestClient(app) as client:
        token_a, cid_a = _nouvelle_conversation(client)
        token_b, cid_b = _nouvelle_conversation(client)

        res_a = client.post(
            f"/api/v1/conversations/{cid_a}/chat",
            headers={"x-session-token": token_a},
            json={"contenu": "Secret confidentiel : code ALPHA-99.", "langue": "fr"},
        )
        assert res_a.status_code == 200

        res_b = client.post(
            f"/api/v1/conversations/{cid_b}/chat",
            headers={"x-session-token": token_b},
            json={"contenu": "Quel est le code secret ?", "langue": "fr"},
        )
        assert res_b.status_code == 200

        contenus_session_b = " ".join(m["content"] for m in faux_llm.appels[-1])
        assert "ALPHA-99" not in contenus_session_b


def test_llm_indisponible_puis_reprise(faux_llm):
    with TestClient(app) as client:
        token, cid = _nouvelle_conversation(client)

        faux_llm.mode = "down"
        res_err = client.post(
            f"/api/v1/conversations/{cid}/chat",
            headers={"x-session-token": token},
            json={"contenu": "Bonjour, es-tu disponible ?", "langue": "fr"},
        )
        assert res_err.status_code in (502, 503)
        detail = res_err.json().get("detail", "")
        assert "Traceback" not in detail
        assert "cle-test-factice" not in detail

        hist_err = client.get(
            f"/api/v1/conversations/{cid}/messages",
            headers={"x-session-token": token},
        )
        assert hist_err.status_code == 200
        assert hist_err.json() == []

        faux_llm.mode = "ok"
        res_ok = client.post(
            f"/api/v1/conversations/{cid}/chat",
            headers={"x-session-token": token},
            json={"contenu": "Bonjour, es-tu disponible ?", "langue": "fr"},
        )
        assert res_ok.status_code == 200


def test_timeout(faux_llm):
    with TestClient(app) as client:
        token, cid = _nouvelle_conversation(client)

        faux_llm.delai_secondes = 0.8
        res = client.post(
            f"/api/v1/conversations/{cid}/chat",
            headers={"x-session-token": token},
            json={"contenu": "Question lente", "langue": "fr"},
        )
        assert res.status_code == 504
        assert "Traceback" not in res.json().get("detail", "")