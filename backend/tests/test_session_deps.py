from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_session, get_db
from app.services.session_service import creer_session


@pytest.fixture
def client_session(db_session):
    """Mini-application avec une seule route protégée par get_current_session."""
    app = FastAPI()

    @app.get("/ping")
    def ping(session=Depends(get_current_session)):
        return {"session_id": session.id}

    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_sans_token_401(client_session):
    assert client_session.get("/ping").status_code == 401


def test_token_inconnu_401(client_session):
    r = client_session.get("/ping", headers={"X-Session-Token": "inconnu"})
    assert r.status_code == 401


def test_token_valide_200(client_session, db_session):
    session, token = creer_session(db_session)
    r = client_session.get("/ping", headers={"X-Session-Token": token})
    assert r.status_code == 200
    assert r.json() == {"session_id": session.id}


def test_token_expire_401(client_session, db_session):
    session, token = creer_session(db_session)
    session.date_expiration = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    r = client_session.get("/ping", headers={"X-Session-Token": token})
    assert r.status_code == 401