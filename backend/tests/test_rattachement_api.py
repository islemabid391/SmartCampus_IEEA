from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.models.catalogue import Etablissement
from app.models.utilisateur import (
    Conversation,
    ProfilAcademique,
    SessionVisiteur,
    Utilisateur,
)
from app.services.memoire_service import mettre_a_jour_memoire
from app.services.session_purge_service import purger_sessions_expirees
from app.services.session_service import hasher_token

URL = "/api/v1/sessions/me/rattachement"
CORPS_OK = {"consentement": True}


def _inscription(client, email="candidat.rattach@example.com"):
    r = client.post("/api/v1/auth/register", json={
        "email": email, "mot_de_passe": "MotDePasse123",
        "nom": "Test", "prenom": "Candidat", "consentement_rgpd": True,
    })
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _visiteur_avec_conversation(client, messages=("Bonjour", "J'aime les maths")):
    token = client.post("/api/v1/sessions").json()["token"]
    entetes = {"X-Session-Token": token}
    cid = client.post("/api/v1/conversations?langue=fr", headers=entetes).json()["id"]
    for texte in messages:
        r = client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"contenu": texte}, headers=entetes,
        )
        assert r.status_code == 201
    return entetes, cid


def test_apercu_avant_rattachement(client):
    visiteur, _ = _visiteur_avec_conversation(client)
    compte = _inscription(client)
    r = client.get(URL, headers={**visiteur, **compte})
    assert r.status_code == 200
    assert r.json() == {"rattachable": True, "nb_conversations": 1, "nb_messages": 2}


def test_apercu_session_vide_non_rattachable(client):
    token = client.post("/api/v1/sessions").json()["token"]
    compte = _inscription(client)
    r = client.get(URL, headers={"X-Session-Token": token, **compte})
    assert r.status_code == 200
    assert r.json()["rattachable"] is False


def test_rattachement_conserve_la_conversation(client):
    visiteur, cid = _visiteur_avec_conversation(client)
    compte = _inscription(client)

    r = client.post(URL, json=CORPS_OK, headers={**visiteur, **compte})
    assert r.status_code == 200
    assert r.json() == {"conversations_rattachees": 1}

    conversations = client.get("/api/v1/me/conversations", headers=compte).json()
    assert [c["id"] for c in conversations] == [cid]

    messages = client.get(f"/api/v1/me/conversations/{cid}/messages", headers=compte).json()
    assert [m["contenu"] for m in messages] == ["Bonjour", "J'aime les maths"]
    assert all(m["date_expiration"] is None for m in messages)


def test_sans_consentement_400_et_rien_ne_change(client):
    visiteur, _ = _visiteur_avec_conversation(client)
    compte = _inscription(client)

    r = client.post(URL, json={"consentement": False}, headers={**visiteur, **compte})
    assert r.status_code == 400
    assert client.get(URL, headers={**visiteur, **compte}).json()["rattachable"] is True
    assert client.get("/api/v1/me/conversations", headers=compte).json() == []


def test_corps_manquant_422(client):
    visiteur, _ = _visiteur_avec_conversation(client)
    compte = _inscription(client)
    assert client.post(URL, json={}, headers={**visiteur, **compte}).status_code == 422


def test_sans_token_visiteur_401(client):
    _visiteur_avec_conversation(client)
    compte = _inscription(client)
    assert client.post(URL, json=CORPS_OK, headers=compte).status_code == 401


def test_sans_jwt_401(client):
    visiteur, _ = _visiteur_avec_conversation(client)
    assert client.post(URL, json=CORPS_OK, headers=visiteur).status_code == 401


def test_token_visiteur_invente_401(client):
    compte = _inscription(client)
    r = client.post(URL, json=CORPS_OK, headers={"X-Session-Token": "token-invente", **compte})
    assert r.status_code == 401


def test_session_expiree_401(client, db_session):
    visiteur, _ = _visiteur_avec_conversation(client)
    compte = _inscription(client)
    session = db_session.scalar(
        select(SessionVisiteur).where(
            SessionVisiteur.token_hash == hasher_token(visiteur["X-Session-Token"])
        )
    )
    session.date_expiration = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.flush()

    assert client.post(URL, json=CORPS_OK, headers={**visiteur, **compte}).status_code == 401


def test_double_rattachement_refuse_et_ancien_token_mort(client):
    visiteur, cid = _visiteur_avec_conversation(client)
    compte = _inscription(client)
    assert client.post(URL, json=CORPS_OK, headers={**visiteur, **compte}).status_code == 200

    # La session est « rattachee » : son token n'ouvre plus rien.
    assert client.post(URL, json=CORPS_OK, headers={**visiteur, **compte}).status_code == 401
    r = client.get(f"/api/v1/conversations/{cid}/messages", headers=visiteur)
    assert r.status_code == 401


def test_un_autre_candidat_ne_voit_pas_la_conversation(client):
    visiteur, cid = _visiteur_avec_conversation(client)
    compte_a = _inscription(client, "a@example.com")
    compte_b = _inscription(client, "b@example.com")
    client.post(URL, json=CORPS_OK, headers={**visiteur, **compte_a})

    r = client.get(f"/api/v1/me/conversations/{cid}/messages", headers=compte_b)
    assert r.status_code == 404
    assert client.get("/api/v1/me/conversations", headers=compte_b).json() == []


def test_la_purge_ne_supprime_pas_les_messages_rattaches(client, db_session):
    visiteur, cid = _visiteur_avec_conversation(client)
    compte = _inscription(client)
    client.post(URL, json=CORPS_OK, headers={**visiteur, **compte})

    purger_sessions_expirees(db_session)

    messages = client.get(f"/api/v1/me/conversations/{cid}/messages", headers=compte).json()
    assert len(messages) == 2


def test_la_memoire_prerempli_le_profil(client, db_session):
    visiteur, cid = _visiteur_avec_conversation(client)
    conversation = db_session.get(Conversation, cid)
    mettre_a_jour_memoire(db_session, conversation, {
        "niveau_scolaire": "Terminale",
        "moyenne": 15.5,
        "centres_interet": ["maths", "informatique"],
        "objectif_professionnel": "Ingénieur logiciel",
    })
    compte = _inscription(client)
    utilisateur_id = client.get("/api/v1/auth/me", headers=compte).json()["id"]

    assert client.post(URL, json=CORPS_OK, headers={**visiteur, **compte}).status_code == 200

    profil = db_session.scalar(
        select(ProfilAcademique).where(ProfilAcademique.utilisateur_id == utilisateur_id)
    )
    assert profil is not None
    assert profil.niveau_scolaire == "Terminale"
    assert float(profil.moyenne) == 15.5
    assert profil.centres_interet == ["maths", "informatique"]
    assert profil.objectif_professionnel == "Ingénieur logiciel"


def test_un_responsable_ne_peut_pas_rattacher_403(client, db_session):
    visiteur, _ = _visiteur_avec_conversation(client)
    iit = db_session.scalar(select(Etablissement).where(Etablissement.code == "IIT"))
    assert iit is not None, "Lance d'abord : python -m scripts.seed"
    db_session.add(Utilisateur(
        email="resp.rattach@example.com",
        mot_de_passe_hash=hash_password("MotDePasse123"),
        role="responsable", nom="R", prenom="R",
        etablissement_id=iit.id, consentement_rgpd=False,
    ))
    db_session.flush()
    token = client.post("/api/v1/auth/login", json={
        "email": "resp.rattach@example.com", "mot_de_passe": "MotDePasse123",
    }).json()["access_token"]

    r = client.post(URL, json=CORPS_OK, headers={**visiteur, "Authorization": f"Bearer {token}"})
    assert r.status_code == 403