import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.session import engine


# =============================================================================
# TABLES ATTENDUES
# =============================================================================

EXPECTED_TABLES = {
    # SA-12 : Catalogue académique
    "etablissement",
    "formation",
    "specialite",
    "programme",
    "matiere",
    "programme_matiere",
    "condition_admission",
    "tarif",
    "passerelle",

    # SA-13 : Gestion des utilisateurs et des interactions
    "utilisateur",
    "session_visiteur",
    "conversation",
    "message",
    "profil_academique",
    "preinscription",
    "demande_equivalence",
    "rendez_vous",
    "entretien",

    # SA-14 : Gestion documentaire
    "document",
    "version_document",
    "chunk_document",
    "tache_synchronisation",
}


# =============================================================================
# FIXTURES ET UTILITAIRES
# =============================================================================

@pytest.fixture(scope="module")
def inspector():
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Base PostgreSQL indisponible")

    return inspect(engine)


def creer_formation_temporaire(conn, code="T_SCHEMA_TEST"):
    """
    Crée une formation temporaire dans la transaction du test.
    L'établissement IIT (id=2) doit être présent dans la base de test.
    """

    resultat = conn.execute(
        text(
            """
            INSERT INTO formation (
                etablissement_id,
                code,
                nom,
                cycle,
                duree_annees
            )
            VALUES (
                2,
                :code,
                'Formation de test schema',
                'ingenieur',
                3
            )
            RETURNING id
            """
        ),
        {"code": code},
    )

    return resultat.scalar_one()


def verifier_integrite_refusee(conn, requete, params):
    """
    Vérifie qu'une requête invalide déclenche une IntegrityError.
    Le SAVEPOINT permet de poursuivre la transaction après l'erreur.
    """

    with pytest.raises(IntegrityError):
        with conn.begin_nested():
            conn.execute(text(requete), params)


# =============================================================================
# 1. VERIFICATION DES TABLES
# =============================================================================

def test_22_tables_presentes(inspector):
    tables = set(inspector.get_table_names())

    assert EXPECTED_TABLES <= tables


def test_index_unique_version_courante(inspector):
    indexes = inspector.get_indexes("version_document")

    noms = {
        index["name"]
        for index in indexes
    }

    assert "uq_version_courante" in noms


# =============================================================================
# 2. VERIFICATION DES CLES ETRANGERES
# =============================================================================

def test_relations_cles_etrangeres_principales(inspector):

    relations_attendues = [
        ("formation", "etablissement_id", "etablissement"),
        ("specialite", "formation_id", "formation"),
        ("tarif", "formation_id", "formation"),
        ("condition_admission", "formation_id", "formation"),
        ("programme", "formation_id", "formation"),
        ("programme_matiere", "programme_id", "programme"),
        ("programme_matiere", "matiere_id", "matiere"),
    ]

    for table, colonne, table_referencee in relations_attendues:

        cles_etrangeres = inspector.get_foreign_keys(table)

        relation_trouvee = any(
            fk["constrained_columns"] == [colonne]
            and fk["referred_table"] == table_referencee
            for fk in cles_etrangeres
        )

        assert relation_trouvee, (
            f"Clé étrangère absente : "
            f"{table}.{colonne} -> {table_referencee}"
        )


# =============================================================================
# 3. VERIFICATION DES CONTRAINTES CHECK
# =============================================================================

def test_check_cycle_formation_refuse_valeur_invalide():

    with engine.connect() as conn:
        transaction = conn.begin()

        try:
            conn.execute(
                text(
                    """
                    INSERT INTO etablissement (code, nom)
                    VALUES ('T_TEST', 'Test')
                    """
                )
            )

            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        """
                        INSERT INTO formation (
                            etablissement_id,
                            code,
                            nom,
                            cycle,
                            duree_annees
                        )
                        SELECT
                            id,
                            'F_TEST',
                            'Formation test',
                            'invalide',
                            3
                        FROM etablissement
                        WHERE code = 'T_TEST'
                        """
                    )
                )

        finally:
            transaction.rollback()


def test_check_tarif_refuse_montant_negatif():

    with engine.connect() as conn:
        transaction = conn.begin()

        try:
            formation_id = creer_formation_temporaire(
                conn,
                "T_SCHEMA_TARIF",
            )

            verifier_integrite_refusee(
                conn,
                """
                INSERT INTO tarif (
                    formation_id,
                    frais_scolarite
                )
                VALUES (
                    :formation_id,
                    -100
                )
                """,
                {"formation_id": formation_id},
            )

        finally:
            transaction.rollback()


def test_check_condition_refuse_type_invalide():

    with engine.connect() as conn:
        transaction = conn.begin()

        try:
            formation_id = creer_formation_temporaire(
                conn,
                "T_SCHEMA_COND",
            )

            verifier_integrite_refusee(
                conn,
                """
                INSERT INTO condition_admission (
                    formation_id,
                    type
                )
                VALUES (
                    :formation_id,
                    'stage'
                )
                """,
                {"formation_id": formation_id},
            )

        finally:
            transaction.rollback()


def test_check_condition_refuse_periode_invalide():

    with engine.connect() as conn:
        transaction = conn.begin()

        try:
            formation_id = creer_formation_temporaire(
                conn,
                "T_SCHEMA_PERIODE",
            )

            verifier_integrite_refusee(
                conn,
                """
                INSERT INTO condition_admission (
                    formation_id,
                    type,
                    valide_du,
                    valide_au
                )
                VALUES (
                    :formation_id,
                    'moyenne',
                    '2027-06-01',
                    '2027-05-01'
                )
                """,
                {"formation_id": formation_id},
            )

        finally:
            transaction.rollback()


# =============================================================================
# 4. VERIFICATION DES CLES ETRANGERES EN BASE
# =============================================================================

def test_fk_tarif_refuse_formation_inexistante():

    with engine.connect() as conn:
        transaction = conn.begin()

        try:
            verifier_integrite_refusee(
                conn,
                """
                INSERT INTO tarif (
                    formation_id,
                    frais_scolarite
                )
                VALUES (
                    999999,
                    3500
                )
                """,
                {},
            )

        finally:
            transaction.rollback()


# =============================================================================
# 5. VERIFICATION DE L'UNICITE
# =============================================================================

def test_formation_refuse_code_duplique():

    with engine.connect() as conn:
        transaction = conn.begin()

        try:
            creer_formation_temporaire(
                conn,
                "T_SCHEMA_UNIQUE",
            )

            verifier_integrite_refusee(
                conn,
                """
                INSERT INTO formation (
                    etablissement_id,
                    code,
                    nom,
                    cycle,
                    duree_annees
                )
                VALUES (
                    2,
                    'T_SCHEMA_UNIQUE',
                    'Deuxieme formation',
                    'ingenieur',
                    3
                )
                """,
                {},
            )

        finally:
            transaction.rollback()