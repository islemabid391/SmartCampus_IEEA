
import pytest
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import engine
from app.api.deps import get_db

from app.api.deps import require_responsable

@pytest.fixture
def responsable_connecte():
    app.dependency_overrides[require_responsable] = lambda: None
    yield
    app.dependency_overrides.pop(require_responsable, None)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
