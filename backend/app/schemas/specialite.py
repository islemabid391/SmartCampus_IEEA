
from pydantic import BaseModel, ConfigDict, Field


class SpecialiteBase(BaseModel):
    formation_id: int = Field(gt=0)
    nom: str = Field(min_length=1, max_length=200)
    description: str | None = None


class SpecialiteCreate(SpecialiteBase):
    pass


class SpecialiteUpdate(BaseModel):
    formation_id: int | None = Field(default=None, gt=0)
    nom: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class SpecialiteResponse(SpecialiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
