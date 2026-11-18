
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.tarif import TarifCreate, TarifUpdate, TarifResponse
from app.services.tarif_service import (
    create_tarif,
    get_tarif_by_id,
    get_all_tarifs,
    update_tarif,
    delete_tarif,
    get_tarifs_officiels,
)


router = APIRouter(
    prefix="/tarifs",
    tags=["Tarifs"]
)


# --------------------------------------------------
# 1. CONSULTATION PUBLIQUE DES TARIFS OFFICIELS
# --------------------------------------------------

@router.get(
    "/officiels",
    response_model=list[TarifResponse],
    summary="Consulter les tarifs officiels"
)
def read_tarifs_officiels(
    formation_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db)
):
    """
    Retourner uniquement les tarifs publiés
    et actuellement valides.
    """

    return get_tarifs_officiels(
        db=db,
        formation_id=formation_id
    )


# --------------------------------------------------
# 2. AJOUTER UN TARIF
# --------------------------------------------------

@router.post(
    "",
    response_model=TarifResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un tarif"
)
def create_tarif_endpoint(
    data: TarifCreate,
    db: Session = Depends(get_db)
):
    try:
        return create_tarif(db=db, data=data)

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de créer le tarif. Vérifiez la formation associée."
        )


# --------------------------------------------------
# 3. CONSULTER TOUS LES TARIFS
# --------------------------------------------------

@router.get(
    "",
    response_model=list[TarifResponse],
    summary="Lister les tarifs"
)
def read_all_tarifs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    formation_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db)
):
    """
    Consultation destinée à la gestion administrative.
    Inclut les brouillons et les tarifs archivés.
    """

    return get_all_tarifs(
        db=db,
        skip=skip,
        limit=limit,
        formation_id=formation_id
    )


# --------------------------------------------------
# 4. CONSULTER UN TARIF PAR ID
# --------------------------------------------------

@router.get(
    "/{tarif_id}",
    response_model=TarifResponse,
    summary="Consulter un tarif par identifiant"
)
def read_tarif(
    tarif_id: int = Path(gt=0),
    db: Session = Depends(get_db)
):
    tarif = get_tarif_by_id(
        db=db,
        tarif_id=tarif_id
    )

    if tarif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarif introuvable."
        )

    return tarif


# --------------------------------------------------
# 5. MODIFIER UN TARIF
# --------------------------------------------------

@router.patch(
    "/{tarif_id}",
    response_model=TarifResponse,
    summary="Modifier un tarif"
)
def update_tarif_endpoint(
    data: TarifUpdate,
    tarif_id: int = Path(gt=0),
    db: Session = Depends(get_db)
):
    try:
        tarif = update_tarif(
            db=db,
            tarif_id=tarif_id,
            data=data
        )

        if tarif is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarif introuvable."
            )

        return tarif

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error)
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Modification impossible. Vérifiez les données du tarif."
        )


# --------------------------------------------------
# 6. SUPPRIMER UN TARIF
# --------------------------------------------------

@router.delete(
    "/{tarif_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un tarif"
)
def remove_tarif(
    tarif_id: int = Path(gt=0),
    db: Session = Depends(get_db)
):
    deleted = delete_tarif(
        db=db,
        tarif_id=tarif_id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarif introuvable."
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
