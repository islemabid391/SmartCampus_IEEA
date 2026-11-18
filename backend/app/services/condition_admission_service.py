
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogue import ConditionAdmission
from app.schemas.condition_admission import (
    ConditionAdmissionCreate,
    ConditionAdmissionUpdate,
)


def create_condition_admission(
    db: Session,
    data: ConditionAdmissionCreate
) -> ConditionAdmission:
    """Créer une nouvelle condition d'admission."""

    condition = ConditionAdmission(**data.model_dump())

    try:
        db.add(condition)
        db.commit()
        db.refresh(condition)
        return condition

    except Exception:
        db.rollback()
        raise


def get_condition_admission_by_id(
    db: Session,
    condition_id: int
) -> ConditionAdmission | None:
    """Récupérer une condition par son identifiant."""

    return db.get(ConditionAdmission, condition_id)


def get_all_conditions_admission(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    formation_id: int | None = None
) -> list[ConditionAdmission]:
    """Récupérer les conditions pour la gestion administrative."""

    statement = select(ConditionAdmission)

    if formation_id is not None:
        statement = statement.where(
            ConditionAdmission.formation_id == formation_id
        )

    statement = (
        statement
        .order_by(ConditionAdmission.id)
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def update_condition_admission(
    db: Session,
    condition_id: int,
    data: ConditionAdmissionUpdate
) -> ConditionAdmission | None:
    """Modifier une condition d'admission existante."""

    condition = db.get(ConditionAdmission, condition_id)

    if condition is None:
        return None

    updates = data.model_dump(exclude_unset=True)

    # Vérifier la cohérence de la période complète.
    date_debut = updates.get("valide_du", condition.valide_du)
    date_fin = updates.get("valide_au", condition.valide_au)

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
        setattr(condition, field, value)

    try:
        db.commit()
        db.refresh(condition)
        return condition

    except Exception:
        db.rollback()
        raise


def delete_condition_admission(
    db: Session,
    condition_id: int
) -> bool:
    """Supprimer une condition d'admission."""

    condition = db.get(ConditionAdmission, condition_id)

    if condition is None:
        return False

    try:
        db.delete(condition)
        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


def get_conditions_admission_officielles(
    db: Session,
    formation_id: int | None = None
) -> list[ConditionAdmission]:
    """
    Consulter uniquement les conditions publiées
    et actuellement valides.
    """

    today = date.today()

    statement = select(ConditionAdmission).where(
        ConditionAdmission.statut_publication == "publie",
        (
            (ConditionAdmission.valide_du.is_(None))
            | (ConditionAdmission.valide_du <= today)
        ),
        (
            (ConditionAdmission.valide_au.is_(None))
            | (ConditionAdmission.valide_au >= today)
        )
    )

    if formation_id is not None:
        statement = statement.where(
            ConditionAdmission.formation_id == formation_id
        )

    statement = statement.order_by(
        ConditionAdmission.formation_id,
        ConditionAdmission.id
    )

    return list(db.scalars(statement).all())
