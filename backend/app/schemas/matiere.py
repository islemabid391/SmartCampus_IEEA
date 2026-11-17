
from pydantic import BaseModel, ConfigDict, Field


class MatiereBase(BaseModel):
    nom: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=30)
    description: str | None = None
    coefficient: float | None = Field(default=None, gt=0)


class MatiereCreate(MatiereBase):
    pass


class MatiereUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=30)
    description: str | None = None
    coefficient: float | None = Field(default=None, gt=0)


class MatiereResponse(MatiereBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
