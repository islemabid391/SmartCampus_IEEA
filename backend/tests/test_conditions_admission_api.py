from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.catalogue import (
    ConditionAdmission,
    Etablissement,
    Formation,
)


# =============================================================================
# FIXTURES
# =============================================================================

def creer_formation(db_session, etablissement_id, code):
    formation = Formation(
        etablissement_id=etablissement_id,
        code=code,
        nom="Formation de test admission",
        cycle="ingenieur",
        duree_annees=3,
    )
    db_session.add(formation)
    db_session.flush()

    return formation


def creer_condition(
    db_session,
    formation_id,
    type_condition="moyenne",
    statut="publie",
    valide_du=None,
    valide_au=None,
):
    condition = ConditionAdmission(
        formation_id=formation_id,
        type=type_condition,
        description="Condition de test",
        valeur_min=Decimal("12"),
        niveau_requis="Baccalauréat",
        statut_publication=statut,
        valide_du=valide_du,
        valide_au=valide_au,
    )
    db_session.add(condition)
    db_session.flush()

    return condition


def get_etablissement(db_session):
    etablissement = db_session.get(Etablissement, 2)

    assert etablissement is not None, (
        "Établissement IIT absent de la base de test"
    )

    return etablissement


# =============================================================================
# CREATION
# =============================================================================

def test_creer_condition_valide(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_CREATE",
    )

    payload = {
        "formation_id": formation.id,
        "type": "moyenne",
        "description": "Moyenne minimale requise",
        "valeur_min": "12",
        "niveau_requis": "Baccalauréat",
        "statut_publication": "publie",
    }

    response = client.post(
        "/api/v1/conditions-admission",
        json=payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["formation_id"] == formation.id
    assert data["type"] == "moyenne"
    assert Decimal(data["valeur_min"]) == Decimal("12")
    assert data["statut_publication"] == "publie"

    condition = db_session.scalar(
        select(ConditionAdmission).where(
            ConditionAdmission.id == data["id"]
        )
    )

    assert condition is not None
    assert condition.description == "Moyenne minimale requise"


def test_rejeter_condition_valeur_min_negative(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_NEGATIVE",
    )

    payload = {
        "formation_id": formation.id,
        "type": "moyenne",
        "valeur_min": "-5",
    }

    response = client.post(
        "/api/v1/conditions-admission",
        json=payload,
    )

    assert response.status_code == 422


def test_rejeter_condition_valeur_min_superieure_a_100(
    client,
    db_session,
):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_SUP_100",
    )

    payload = {
        "formation_id": formation.id,
        "type": "moyenne",
        "valeur_min": "105",
    }

    response = client.post(
        "/api/v1/conditions-admission",
        json=payload,
    )

    assert response.status_code == 422


def test_rejeter_condition_sans_formation_id(client):
    payload = {
        "type": "moyenne",
        "valeur_min": "12",
    }

    response = client.post(
        "/api/v1/conditions-admission",
        json=payload,
    )

    assert response.status_code == 422


def test_rejeter_condition_type_invalide(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_TYPE",
    )

    payload = {
        "formation_id": formation.id,
        "type": "stage",
        "valeur_min": "12",
    }

    response = client.post(
        "/api/v1/conditions-admission",
        json=payload,
    )

    assert response.status_code == 422


def test_rejeter_condition_formation_inexistante(client):
    payload = {
        "formation_id": 999999,
        "type": "moyenne",
        "valeur_min": "12",
    }

    response = client.post(
        "/api/v1/conditions-admission",
        json=payload,
    )

    assert response.status_code == 409


def test_rejeter_condition_periode_invalide(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_PERIODE",
    )

    payload = {
        "formation_id": formation.id,
        "type": "moyenne",
        "valeur_min": "12",
        "valide_du": "2027-06-01",
        "valide_au": "2027-05-01",
    }

    response = client.post(
        "/api/v1/conditions-admission",
        json=payload,
    )

    assert response.status_code == 422


# =============================================================================
# CONSULTATION
# =============================================================================

def test_consulter_condition_par_id(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_GET",
    )
    condition = creer_condition(
        db_session,
        formation.id,
    )

    response = client.get(
        f"/api/v1/conditions-admission/{condition.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == condition.id
    assert data["type"] == "moyenne"
    assert data["formation_id"] == formation.id


def test_consulter_condition_inexistante(client):
    response = client.get(
        "/api/v1/conditions-admission/999999"
    )

    assert response.status_code == 404


def test_consulter_condition_identifiant_invalide(client):
    response = client.get(
        "/api/v1/conditions-admission/0"
    )

    assert response.status_code == 422


def test_lister_conditions_par_formation(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_LIST",
    )
    condition = creer_condition(
        db_session,
        formation.id,
    )

    response = client.get(
        "/api/v1/conditions-admission",
        params={"formation_id": formation.id},
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert any(
        item["id"] == condition.id
        for item in data
    )
    assert all(
        item["formation_id"] == formation.id
        for item in data
    )


def test_paginer_liste_conditions(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_PAGINATION",
    )

    premiere = creer_condition(
        db_session,
        formation.id,
    )
    deuxieme = creer_condition(
        db_session,
        formation.id,
    )

    page_1 = client.get(
        "/api/v1/conditions-admission",
        params={
            "formation_id": formation.id,
            "skip": 0,
            "limit": 1,
        },
    )

    page_2 = client.get(
        "/api/v1/conditions-admission",
        params={
            "formation_id": formation.id,
            "skip": 1,
            "limit": 1,
        },
    )

    assert page_1.status_code == 200
    assert page_2.status_code == 200

    assert len(page_1.json()) == 1
    assert len(page_2.json()) == 1

    assert page_1.json()[0]["id"] != page_2.json()[0]["id"]

    ids = {
        page_1.json()[0]["id"],
        page_2.json()[0]["id"],
    }

    assert ids == {premiere.id, deuxieme.id}


def test_rejeter_parametres_pagination_invalides(client):
    response_skip = client.get(
        "/api/v1/conditions-admission",
        params={"skip": -1},
    )

    response_limit = client.get(
        "/api/v1/conditions-admission",
        params={"limit": 0},
    )

    response_limit_max = client.get(
        "/api/v1/conditions-admission",
        params={"limit": 101},
    )

    assert response_skip.status_code == 422
    assert response_limit.status_code == 422
    assert response_limit_max.status_code == 422


def test_consulter_conditions_officielles(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_OFFICIELLE",
    )
    condition = creer_condition(
        db_session,
        formation.id,
        statut="publie",
    )

    response = client.get(
        "/api/v1/conditions-admission/officielles",
        params={"formation_id": formation.id},
    )

    assert response.status_code == 200

    data = response.json()

    assert any(
        item["id"] == condition.id
        for item in data
    )

    assert all(
        item["statut_publication"] == "publie"
        for item in data
    )


def test_conditions_officielles_excluent_brouillons_et_perimees(
    client,
    db_session,
):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_FILTRE_OFFICIEL",
    )

    condition_publiee = creer_condition(
        db_session,
        formation.id,
        statut="publie",
    )

    condition_brouillon = creer_condition(
        db_session,
        formation.id,
        statut="brouillon",
    )

    condition_expiree = creer_condition(
        db_session,
        formation.id,
        statut="publie",
        valide_du=date(2000, 1, 1),
        valide_au=date(2001, 1, 1),
    )

    condition_future = creer_condition(
        db_session,
        formation.id,
        statut="publie",
        valide_du=date(2099, 1, 1),
        valide_au=date(2099, 12, 31),
    )

    response = client.get(
        "/api/v1/conditions-admission/officielles",
        params={"formation_id": formation.id},
    )

    assert response.status_code == 200

    ids = {
        item["id"]
        for item in response.json()
    }

    assert condition_publiee.id in ids
    assert condition_brouillon.id not in ids
    assert condition_expiree.id not in ids
    assert condition_future.id not in ids


# =============================================================================
# MODIFICATION
# =============================================================================

def test_modifier_condition_valide(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_PATCH",
    )
    condition = creer_condition(
        db_session,
        formation.id,
    )

    payload = {
        "description": "Nouvelle moyenne minimale requise",
        "valeur_min": "14",
    }

    response = client.patch(
        f"/api/v1/conditions-admission/{condition.id}",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["description"] == "Nouvelle moyenne minimale requise"
    assert Decimal(data["valeur_min"]) == Decimal("14")


def test_rejeter_modification_periode_invalide(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_PATCH_DATE",
    )
    condition = creer_condition(
        db_session,
        formation.id,
    )

    payload = {
        "valide_du": "2027-06-01",
        "valide_au": "2027-05-01",
    }

    response = client.patch(
        f"/api/v1/conditions-admission/{condition.id}",
        json=payload,
    )

    assert response.status_code == 422


def test_rejeter_modification_periode_invalide_partielle(
    client,
    db_session,
):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
       "TEST_COND_PATCH_PART",
    )

    condition = creer_condition(
        db_session,
        formation.id,
        valide_du=date(2027, 6, 1),
    )

    response = client.patch(
        f"/api/v1/conditions-admission/{condition.id}",
        json={"valide_au": "2027-05-01"},
    )

    assert response.status_code == 422


def test_rejeter_modification_valeur_min_invalide(
    client,
    db_session,
):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_PATCH_VALEUR",
    )
    condition = creer_condition(
        db_session,
        formation.id,
    )

    response = client.patch(
        f"/api/v1/conditions-admission/{condition.id}",
        json={"valeur_min": "150"},
    )

    assert response.status_code == 422


def test_rejeter_modification_formation_inexistante(
    client,
    db_session,
):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_PATCH_FK",
    )
    condition = creer_condition(
        db_session,
        formation.id,
    )

    response = client.patch(
        f"/api/v1/conditions-admission/{condition.id}",
        json={"formation_id": 999999},
    )

    assert response.status_code == 409


def test_modifier_condition_inexistante(client):
    response = client.patch(
        "/api/v1/conditions-admission/999999",
        json={"description": "Modification"},
    )

    assert response.status_code == 404


# =============================================================================
# SUPPRESSION
# =============================================================================

def test_supprimer_condition(client, db_session):
    etablissement = get_etablissement(db_session)
    formation = creer_formation(
        db_session,
        etablissement.id,
        "TEST_CONDITION_DELETE",
    )
    condition = creer_condition(
        db_session,
        formation.id,
    )

    condition_id = condition.id

    response = client.delete(
        f"/api/v1/conditions-admission/{condition_id}"
    )

    assert response.status_code == 204

    verification = client.get(
        f"/api/v1/conditions-admission/{condition_id}"
    )

    assert verification.status_code == 404


def test_supprimer_condition_inexistante(client):
    response = client.delete(
        "/api/v1/conditions-admission/999999"
    )

    assert response.status_code == 404