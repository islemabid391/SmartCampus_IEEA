import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.db.session import SessionLocal, engine
from app.models.catalogue import Formation, Matiere, ProgrammeMatiere, Tarif
from app.models.utilisateur import Utilisateur
from scripts.seed import main


@pytest.fixture(scope="module", autouse=True)
def base_disponible():
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Base PostgreSQL indisponible")


def _comptes():
    with SessionLocal() as db:
        return tuple(
            db.scalar(select(func.count()).select_from(m))
            for m in (Formation, Matiere, ProgrammeMatiere, Tarif, Utilisateur)
        )


def test_seed_est_idempotent():
    main()
    premier = _comptes()
    main()
    assert _comptes() == premier


def test_donnees_attendues():
    main()
    with SessionLocal() as db:
        responsables = db.scalar(
            select(func.count()).select_from(Utilisateur).where(Utilisateur.role == "responsable")
        )
        brouillons = db.scalar(
            select(func.count()).select_from(Formation).where(Formation.statut_publication == "brouillon")
        )
        hashes = db.scalars(select(Utilisateur.mot_de_passe_hash)).all()
    assert responsables >= 2
    assert brouillons >= 1
    assert all(h.startswith("$2") for h in hashes)