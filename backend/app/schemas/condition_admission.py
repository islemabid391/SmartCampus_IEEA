
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


TypeCondition = Literal["diplome", "moyenne", "concours", "dossier"]
StatutPublication = Literal["brouillon", "publie", "archive"]


class ConditionAdmissionBase(BaseModel):
    formation_id: int = Field(gt=0)
    type: TypeCondition
    description: str | None = None
    valeur_min: Decimal | None = Field(default=None, ge=0, le=100)
    niveau_requis: str | None = Field(default=None, max_length=100)
    statut_publication: StatutPublication = "brouillon"
    valide_du: date | None = None
    valide_au: date | None = None

    @model_validator(mode="after")
    def verifier_periode(self):
        if (
            self.valide_du is not None
            and self.valide_au is not None
            and self.valide_au < self.valide_du
        ):
            raise ValueError("La date de fin doit être supérieure ou égale à la date de début.")
        return self


class ConditionAdmissionCreate(ConditionAdmissionBase):
    """Schema used to create an admission condition."""
    pass


class ConditionAdmissionUpdate(BaseModel):
    """Schema used to update only the provided fields."""

    formation_id: int | None = Field(default=None, gt=0)
    type: TypeCondition | None = None
    description: str | None = None
    valeur_min: Decimal | None = Field(default=None, ge=0, le=100)
    niveau_requis: str | None = Field(default=None, max_length=100)
    statut_publication: StatutPublication | None = None
    valide_du: date | None = None
    valide_au: date | None = None

    @model_validator(mode="after")
    def verifier_periode(self):
        if (
            self.valide_du is not None
            and self.valide_au is not None
            and self.valide_au < self.valide_du
        ):
            raise ValueError("La date de fin doit être supérieure ou égale à la date de début.")
        return self


class ConditionAdmissionResponse(ConditionAdmissionBase):
    """Schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
