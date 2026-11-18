
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogue import Tarif
from app.schemas.tarif import TarifCreate, TarifUpdate


def create_tarif(db: Session, data: TarifCreate) -> Tarif:
    """Créer un nouveau tarif."""

    tarif = Tarif(**data.model_dump())

    try:
        db.add(tarif)
        db.commit()
        db.refresh(tarif)
        return tarif

    except Exception:
        db.rollback()
        raise


def get_tarif_by_id(db: Session, tarif_id: int) -> Tarif | None:
    """Récupérer un tarif par son identifiant."""

    return db.get(Tarif, tarif_id)


def get_all_tarifs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    formation_id: int | None = None
) -> list[Tarif]:
    """Récupérer les tarifs pour la gestion administrative."""

    statement = select(Tarif)

    if formation_id is not None:
        statement = statement.where(
            Tarif.formation_id == formation_id
        )

    statement = (
        statement
        .order_by(Tarif.id)
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def update_tarif(
    db: Session,
    tarif_id: int,
    data: TarifUpdate
) -> Tarif | None:
    """Modifier un tarif existant."""

    tarif = db.get(Tarif, tarif_id)

    if tarif is None:
        return None

    updates = data.model_dump(exclude_unset=True)

    # Vérifier la période complète, y compris les valeurs
    # déjà enregistrées qui ne sont pas fournies dans la requête.
    date_debut = updates.get("valide_du", tarif.valide_du)
    date_fin = updates.get("valide_au", tarif.valide_au)

    if (
        date_debut is not None
        and date_fin is not None
        and date_fin < date_debut
    ):
        raise ValueError(
            "La date de fin doit être supérieure "
            "ou égale à la date de début."
        )

    for field, value in updates.items():
        setattr(tarif, field, value)

    try:
        db.commit()
        db.refresh(tarif)
        return tarif

    except Exception:
        db.rollback()
        raise


def delete_tarif(db: Session, tarif_id: int) -> bool:
    """Supprimer un tarif."""

    tarif = db.get(Tarif, tarif_id)

    if tarif is None:
        return False

    try:
        db.delete(tarif)
        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


def get_tarifs_officiels(
    db: Session,
    formation_id: int | None = None
) -> list[Tarif]:
    """
    Consulter uniquement les tarifs officiellement publiés
    et actuellement valides.
    """

    today = date.today()

    statement = select(Tarif).where(
        Tarif.statut_publication == "publie",
        (
            (Tarif.valide_du.is_(None))
            | (Tarif.valide_du <= today)
        ),
        (
            (Tarif.valide_au.is_(None))
            | (Tarif.valide_au >= today)
        )
    )

    if formation_id is not None:
        statement = statement.where(
            Tarif.formation_id == formation_id
        )

    statement = statement.order_by(Tarif.formation_id, Tarif.id)

    return list(db.scalars(statement).all())
