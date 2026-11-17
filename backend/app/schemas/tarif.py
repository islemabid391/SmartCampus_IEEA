
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TarifBase(BaseModel):
    formation_id: int = Field(gt=0)
    montant: float = Field(ge=0)
    devise: str = Field(default="TND", min_length=3, max_length=3)
    description: str | None = None
    date_debut_validite: date | None = None
    date_fin_validite: date | None = None


class TarifCreate(TarifBase):
    pass


class TarifUpdate(BaseModel):
    formation_id: int | None = Field(default=None, gt=0)
    montant: float | None = Field(default=None, ge=0)
    devise: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = None
    date_debut_validite: date | None = None
    date_fin_validite: date | None = None


class TarifResponse(TarifBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
