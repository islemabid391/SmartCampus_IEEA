from sqlalchemy import select

from app.core.security import hash_password
from app.models.catalogue import Etablissement, Formation
from app.models.utilisateur import Utilisateur


def _inscription(client, email="test@example.com"):
    return client.post("/api/v1/auth/register", json={
        "email": email, "mot_de_passe": "MotDePasse123", "nom": "Test",
        "prenom": "User", "consentement_rgpd": True,
    })

def _creer_responsable_et_token(client, db_session):
    """Insère un responsable IIT en base, se connecte, retourne (token, formation_id)."""
    iit = db_session.scalar(select(Etablissement).where(Etablissement.code == "IIT"))
    assert iit is not None, "Établissement IIT absent : lance d'abord python -m scripts.seed"

    responsable = Utilisateur(
        email="responsable.test@example.com",
        mot_de_passe_hash=hash_password("MotDePasse123"),
        role="responsable",
        nom="Test",
        prenom="Responsable",
        etablissement_id=iit.id,
        consentement_rgpd=False,
    )
    formation = Formation(
        etablissement_id=iit.id,
        code="TEST_AUTH_RESPONSABLE",
        nom="Formation test auth",
        cycle="ingenieur",
        duree_annees=3,
    )
    db_session.add_all([responsable, formation])
    db_session.flush()  # indispensable : autoflush est désactivé dans conftest

    r = client.post("/api/v1/auth/login", json={
        "email": "responsable.test@example.com",
        "mot_de_passe": "MotDePasse123",
    })
    assert r.status_code == 200
    return r.json()["access_token"], formation.id

def test_inscription_puis_login_puis_me(client):
    assert _inscription(client).status_code == 201
    r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "mot_de_passe": "MotDePasse123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["role"] == "candidat"
    assert "mot_de_passe_hash" not in me.json()


def test_email_deja_utilise_409(client):
    _inscription(client)
    assert _inscription(client).status_code == 409


def test_mauvais_mot_de_passe_401(client):
    _inscription(client)
    r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "mot_de_passe": "faux-mot-de-passe"})
    assert r.status_code == 401


def test_consentement_obligatoire(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "mot_de_passe": "MotDePasse123", "nom": "A", "prenom": "B",
        "consentement_rgpd": False})
    assert r.status_code == 422


def test_candidat_ne_peut_pas_creer_un_tarif_403(client):
    token = _inscription(client).json()["access_token"]
    r = client.post("/api/v1/tarifs", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403  # la dépendance de rôle passe avant la validation du corps


def test_sans_token_401_sur_route_protegee(client):
    assert client.post("/api/v1/tarifs", json={}).status_code == 401


def test_routes_publiques_et_chat_visiteur_restent_libres(client):
    assert client.get("/api/v1/tarifs/officiels").status_code == 200
    r = client.post("/api/v1/sessions")
    assert r.status_code == 201
    h = {"X-Session-Token": r.json()["token"]}
    assert client.post("/api/v1/conversations", headers=h).status_code == 201
    
       
def test_responsable_peut_creer_un_tarif(client, db_session):
    token, formation_id = _creer_responsable_et_token(client, db_session)

    r = client.post(
        "/api/v1/tarifs",
        json={
            "formation_id": formation_id,
            "frais_scolarite": "3500.00",
            "devise": "TND",
            "statut_publication": "publie",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201


def test_responsable_peut_lister_les_tarifs_non_publies(client, db_session):
    token, _ = _creer_responsable_et_token(client, db_session)
    r = client.get("/api/v1/tarifs", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_candidat_ne_peut_pas_lister_tous_les_tarifs(client):
    token = _inscription(client).json()["access_token"]
    r = client.get("/api/v1/tarifs", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403    