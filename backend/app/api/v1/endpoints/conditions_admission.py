
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.condition_admission import (
    ConditionAdmissionCreate,
    ConditionAdmissionUpdate,
    ConditionAdmissionResponse,
)
from app.services.condition_admission_service import (
    create_condition_admission,
    get_condition_admission_by_id,
    get_all_conditions_admission,
    update_condition_admission,
    delete_condition_admission,
    get_conditions_admission_officielles,
)


router = APIRouter(
    prefix="/conditions-admission",
    tags=["Conditions d'admission"]
)


# --------------------------------------------------
# 1. CONSULTATION PUBLIQUE DES CONDITIONS OFFICIELLES
# --------------------------------------------------

@router.get(
    "/officielles",
    response_model=list[ConditionAdmissionResponse],
    summary="Consulter les conditions d'admission officielles"
)
def read_conditions_admission_officielles(
    formation_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db)
):
    """
    Retourner uniquement les conditions publiées
    et actuellement valides.
    """

    return get_conditions_admission_officielles(
        db=db,
        formation_id=formation_id
    )


# --------------------------------------------------
# 2. CRÉER UNE CONDITION D'ADMISSION
# --------------------------------------------------

@router.post(
    "",
    response_model=ConditionAdmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une condition d'admission"
)
def create_condition_admission_endpoint(
    data: ConditionAdmissionCreate,
    db: Session = Depends(get_db)
):
    try:
        return create_condition_admission(
            db=db,
            data=data
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Impossible de créer la condition. "
                "Vérifiez la formation associée."
            )
        )


# --------------------------------------------------
# 3. LISTER LES CONDITIONS D'ADMISSION
# --------------------------------------------------

@router.get(
    "",
    response_model=list[ConditionAdmissionResponse],
    summary="Lister les conditions d'admission"
)
def read_all_conditions_admission(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    formation_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db)
):
    """
    Consultation destinée à la gestion administrative.
    Inclut les brouillons et les conditions archivées.
    """

    return get_all_conditions_admission(
        db=db,
        skip=skip,
        limit=limit,
        formation_id=formation_id
    )


# --------------------------------------------------
# 4. CONSULTER UNE CONDITION PAR ID
# --------------------------------------------------

@router.get(
    "/{condition_id}",
    response_model=ConditionAdmissionResponse,
    summary="Consulter une condition par identifiant"
)
def read_condition_admission(
    condition_id: int = Path(gt=0),
    db: Session = Depends(get_db)
):
    condition = get_condition_admission_by_id(
        db=db,
        condition_id=condition_id
    )

    if condition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Condition d'admission introuvable."
        )

    return condition


# --------------------------------------------------
# 5. MODIFIER UNE CONDITION
# --------------------------------------------------

@router.patch(
    "/{condition_id}",
    response_model=ConditionAdmissionResponse,
    summary="Modifier une condition d'admission"
)
def update_condition_admission_endpoint(
    data: ConditionAdmissionUpdate,
    condition_id: int = Path(gt=0),
    db: Session = Depends(get_db)
):
    try:
        condition = update_condition_admission(
            db=db,
            condition_id=condition_id,
            data=data
        )

        if condition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Condition d'admission introuvable."
            )

        return condition

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Modification impossible. "
                "Vérifiez les données de la condition."
            )
        )


# --------------------------------------------------
# 6. SUPPRIMER UNE CONDITION
# --------------------------------------------------

@router.delete(
    "/{condition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une condition d'admission"
)
def remove_condition_admission(
    condition_id: int = Path(gt=0),
    db: Session = Depends(get_db)
):
    deleted = delete_condition_admission(
        db=db,
        condition_id=condition_id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Condition d'admission introuvable."
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
