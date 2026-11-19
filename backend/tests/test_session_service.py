from app.core.config import settings
from app.services.session_service import generer_token, hasher_token


def test_reglages_sessions_par_defaut():
    assert settings.session_ttl_minutes > 0
    assert settings.session_max_messages > 0
    assert settings.session_max_conversations > 0


def test_tokens_uniques():
    assert generer_token() != generer_token()


def test_hash_fait_64_caracteres_et_est_deterministe():
    token = generer_token()
    assert len(hasher_token(token)) == 64  # taille de session_visiteur.token_hash
    assert hasher_token(token) == hasher_token(token)
    assert hasher_token(token) != token


# ---------- Étape 3 : nécessite PostgreSQL (docker compose up -d db) ----------
from datetime import datetime, timedelta, timezone

from app.services.session_service import creer_session, get_session_valide


def test_creer_session(db_session):
    session, token = creer_session(db_session)

    assert session.id is not None
    assert session.statut == "active"
    assert session.token_hash == hasher_token(token)
    assert session.token_hash != token  # le token en clair n'est pas stocké

    attendu = datetime.now(timezone.utc) + timedelta(minutes=settings.session_ttl_minutes)
    assert abs((session.date_expiration - attendu).total_seconds()) < 5


# ---------- Étape 4 : retrouver / valider une session ----------
def test_get_session_valide_ok(db_session):
    session, token = creer_session(db_session)
    trouvee = get_session_valide(db_session, token)
    assert trouvee is not None
    assert trouvee.id == session.id


def test_get_session_valide_token_inconnu(db_session):
    assert get_session_valide(db_session, "token-qui-n-existe-pas") is None


def test_get_session_valide_expiree(db_session):
    session, token = creer_session(db_session)
    session.date_expiration = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    assert get_session_valide(db_session, token) is None
    db_session.refresh(session)
    assert session.statut == "expiree"  # marquée expirée en base