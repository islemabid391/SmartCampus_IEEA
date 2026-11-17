
from pydantic import BaseModel, ConfigDict, Field


class ProgrammeBase(BaseModel):
    specialite_id: int = Field(gt=0)
    nom: str = Field(min_length=1, max_length=200)
    description: str | None = None
    duree_semestres: int | None = Field(default=None, gt=0)


class ProgrammeCreate(ProgrammeBase):
    """Schema used to create a programme."""
    pass


class ProgrammeUpdate(BaseModel):
    """Schema used to update only the provided fields."""

    specialite_id: int | None = Field(default=None, gt=0)
    nom: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    duree_semestres: int | None = Field(default=None, gt=0)


class ProgrammeResponse(ProgrammeBase):
    """Schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
