import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.session import engine

EXPECTED_TABLES = {
    # SA-12
    "etablissement", "formation", "specialite", "programme", "matiere",
    "programme_matiere", "condition_admission", "tarif", "passerelle",
    # SA-13
    "utilisateur", "session_visiteur", "conversation", "message",
    "profil_academique", "preinscription", "demande_equivalence",
    "rendez_vous", "entretien",
    # SA-14
    "document", "version_document", "chunk_document", "tache_synchronisation",
}


@pytest.fixture(scope="module")
def inspector():
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Base PostgreSQL indisponible")
    return inspect(engine)


def test_22_tables_presentes(inspector):
    assert EXPECTED_TABLES <= set(inspector.get_table_names())


def test_index_unique_version_courante(inspector):
    noms = {i["name"] for i in inspector.get_indexes("version_document")}
    assert "uq_version_courante" in noms


def test_check_cycle_formation_refuse_valeur_invalide():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text("INSERT INTO etablissement (code, nom) VALUES ('T_TEST', 'Test')"))
            with pytest.raises(IntegrityError):
                conn.execute(text(
                    "INSERT INTO formation (etablissement_id, code, nom, cycle, duree_annees) "
                    "SELECT id, 'F_TEST', 'F', 'invalide', 3 FROM etablissement WHERE code = 'T_TEST'"
                ))
        finally:
            trans.rollback()