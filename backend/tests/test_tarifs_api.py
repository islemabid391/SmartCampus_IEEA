from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.catalogue import Etablissement, Formation, Tarif


@pytest.fixture
def formation_test(db_session):
    etablissement = db_session.get(Etablissement, 2)
    assert etablissement is not None, "Établissement IIT absent de la base de test"

    formation = Formation(
        etablissement_id=etablissement.id,
        code="TEST_TARIF_API",
        nom="Formation de test API",
        cycle="ingenieur",
        duree_annees=3,
    )
    db_session.add(formation)
    db_session.flush()

    return formation


@pytest.fixture
def tarif_test(db_session, formation_test):
    tarif = Tarif(
        formation_id=formation_test.id,
        frais_scolarite=Decimal("3500.00"),
        devise="TND",
        statut_publication="publie",
    )
    db_session.add(tarif)
    db_session.flush()

    return tarif


# -----------------------------------------------------------------------------
# CREATION
# -----------------------------------------------------------------------------


def test_creer_tarif_valide(client, db_session, formation_test):
    payload = {
        "formation_id": formation_test.id,
        "frais_scolarite": "3500.00",
        "devise": "TND",
        "statut_publication": "publie",
    }

    response = client.post("/api/v1/tarifs", json=payload)

    assert response.status_code == 201

    data = response.json()
    assert data["formation_id"] == formation_test.id
    assert Decimal(data["frais_scolarite"]) == Decimal("3500.00")
    assert data["devise"] == "TND"
    assert data["statut_publication"] == "publie"

    tarif = db_session.scalar(
        select(Tarif).where(Tarif.id == data["id"])
    )

    assert tarif is not None
    assert tarif.frais_scolarite == Decimal("3500.00")


def test_rejeter_tarif_montant_negatif(client, formation_test):
    payload = {
        "formation_id": formation_test.id,
        "frais_scolarite": "-100.00",
        "devise": "TND",
    }

    response = client.post("/api/v1/tarifs", json=payload)

    assert response.status_code == 422


def test_rejeter_tarif_sans_formation_id(client):
    payload = {
        "frais_scolarite": "3500.00",
        "devise": "TND",
    }

    response = client.post("/api/v1/tarifs", json=payload)

    assert response.status_code == 422


def test_rejeter_tarif_devise_invalide(client, formation_test):
    payload = {
        "formation_id": formation_test.id,
        "frais_scolarite": "3500.00",
        "devise": "EURO",
    }

    response = client.post("/api/v1/tarifs", json=payload)

    assert response.status_code == 422


def test_rejeter_tarif_formation_inexistante(client):
    payload = {
        "formation_id": 999999,
        "frais_scolarite": "3500.00",
        "devise": "TND",
    }

    response = client.post("/api/v1/tarifs", json=payload)

    assert response.status_code == 409


def test_rejeter_tarif_periode_invalide(client, formation_test):
    payload = {
        "formation_id": formation_test.id,
        "frais_scolarite": "3500.00",
        "devise": "TND",
        "valide_du": "2027-06-01",
        "valide_au": "2027-05-01",
    }

    response = client.post("/api/v1/tarifs", json=payload)

    assert response.status_code == 422


# -----------------------------------------------------------------------------
# CONSULTATION
# -----------------------------------------------------------------------------


def test_consulter_tarif_par_id(client, tarif_test):
    response = client.get(f"/api/v1/tarifs/{tarif_test.id}")

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == tarif_test.id
    assert data["formation_id"] == tarif_test.formation_id
    assert Decimal(data["frais_scolarite"]) == Decimal("3500.00")


def test_consulter_tarif_inexistant(client):
    response = client.get("/api/v1/tarifs/999999")

    assert response.status_code == 404


def test_consulter_tarif_identifiant_invalide(client):
    response = client.get("/api/v1/tarifs/0")

    assert response.status_code == 422


def test_lister_tarifs_par_formation(client, tarif_test):
    response = client.get(
        "/api/v1/tarifs",
        params={"formation_id": tarif_test.formation_id},
    )

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert data

    assert all(
        item["formation_id"] == tarif_test.formation_id
        for item in data
    )

    assert any(
        item["id"] == tarif_test.id
        for item in data
    )


def test_paginer_liste_tarifs(client, db_session, tarif_test, formation_test):
    second_tarif = Tarif(
        formation_id=formation_test.id,
        frais_scolarite=Decimal("4000.00"),
        devise="TND",
        statut_publication="brouillon",
    )

    db_session.add(second_tarif)
    db_session.flush()

    page_1 = client.get(
        "/api/v1/tarifs",
        params={
            "formation_id": formation_test.id,
            "skip": 0,
            "limit": 1,
        },
    )

    page_2 = client.get(
        "/api/v1/tarifs",
        params={
            "formation_id": formation_test.id,
            "skip": 1,
            "limit": 1,
        },
    )

    assert page_1.status_code == 200
    assert page_2.status_code == 200

    assert len(page_1.json()) == 1
    assert len(page_2.json()) == 1

    assert page_1.json()[0]["id"] != page_2.json()[0]["id"]


def test_rejeter_parametres_pagination_tarifs_invalides(client):
    response_skip = client.get(
        "/api/v1/tarifs",
        params={"skip": -1},
    )

    response_limit = client.get(
        "/api/v1/tarifs",
        params={"limit": 0},
    )

    assert response_skip.status_code == 422
    assert response_limit.status_code == 422


def test_consulter_tarifs_officiels_exclut_brouillons_et_expires(
    client, db_session, tarif_test, formation_test
):
    tarif_brouillon = Tarif(
        formation_id=formation_test.id,
        frais_scolarite=Decimal("3800.00"),
        devise="TND",
        statut_publication="brouillon",
    )

    tarif_expire = Tarif(
        formation_id=formation_test.id,
        frais_scolarite=Decimal("3900.00"),
        devise="TND",
        statut_publication="publie",
        valide_du=date(2000, 1, 1),
        valide_au=date(2001, 1, 1),
    )

    db_session.add_all([tarif_brouillon, tarif_expire])
    db_session.flush()

    response = client.get(
        "/api/v1/tarifs/officiels",
        params={"formation_id": formation_test.id},
    )

    assert response.status_code == 200

    data = response.json()
    ids = {item["id"] for item in data}

    assert tarif_test.id in ids
    assert tarif_brouillon.id not in ids
    assert tarif_expire.id not in ids

    assert all(
        item["statut_publication"] == "publie"
        for item in data
    )


# -----------------------------------------------------------------------------
# MODIFICATION
# -----------------------------------------------------------------------------


def test_modifier_tarif_valide(client, tarif_test):
    response = client.patch(
        f"/api/v1/tarifs/{tarif_test.id}",
        json={"frais_scolarite": "4200.00"},
    )

    assert response.status_code == 200

    data = response.json()
    assert Decimal(data["frais_scolarite"]) == Decimal("4200.00")


def test_rejeter_modification_tarif_montant_negatif(client, tarif_test):
    response = client.patch(
        f"/api/v1/tarifs/{tarif_test.id}",
        json={"frais_scolarite": "-10.00"},
    )

    assert response.status_code == 422


def test_rejeter_modification_tarif_periode_invalide(client, tarif_test):
    response = client.patch(
        f"/api/v1/tarifs/{tarif_test.id}",
        json={
            "valide_du": "2027-06-01",
            "valide_au": "2027-05-01",
        },
    )

    assert response.status_code == 422


def test_modifier_tarif_inexistant(client):
    response = client.patch(
        "/api/v1/tarifs/999999",
        json={"frais_scolarite": "4200.00"},
    )

    assert response.status_code == 404


# -----------------------------------------------------------------------------
# SUPPRESSION
# -----------------------------------------------------------------------------


def test_supprimer_tarif(client, tarif_test):
    tarif_id = tarif_test.id

    response = client.delete(f"/api/v1/tarifs/{tarif_id}")

    assert response.status_code == 204

    verification = client.get(f"/api/v1/tarifs/{tarif_id}")

    assert verification.status_code == 404


def test_supprimer_tarif_inexistant(client):
    response = client.delete("/api/v1/tarifs/999999")

    assert response.status_code == 404