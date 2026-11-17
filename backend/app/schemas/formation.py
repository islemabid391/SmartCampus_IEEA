
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CycleFormation = Literal["licence", "prepa", "ingenieur", "autre"]


class FormationBase(BaseModel):
    etablissement_id: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=30)
    nom: str = Field(min_length=1, max_length=200)
    cycle: CycleFormation
    duree_annees: int = Field(gt=0)

    modalites: str | None = Field(default=None, max_length=100)
    langue: str | None = Field(default=None, max_length=30)
    description: str | None = None
    debouches: str | None = None


class FormationCreate(FormationBase):
    """Schema used to create a formation."""
    pass


class FormationUpdate(BaseModel):
    """Schema used to update only the provided fields."""

    etablissement_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, min_length=1, max_length=30)
    nom: str | None = Field(default=None, min_length=1, max_length=200)
    cycle: CycleFormation | None = None
    duree_annees: int | None = Field(default=None, gt=0)

    modalites: str | None = Field(default=None, max_length=100)
    langue: str | None = Field(default=None, max_length=30)
    description: str | None = None
    debouches: str | None = None


class FormationResponse(FormationBase):
    """Schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    statut_publication: Literal["brouillon", "publie", "archive"]
