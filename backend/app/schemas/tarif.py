
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


StatutPublication = Literal["brouillon", "publie", "archive"]


class TarifBase(BaseModel):
    formation_id: int = Field(gt=0)
    frais_scolarite: Decimal = Field(ge=0)
    devise: str = Field(default="TND", min_length=3, max_length=3)
    modalites_paiement: str | None = None
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


class TarifCreate(TarifBase):
    """Schema used to create an official tariff."""
    pass


class TarifUpdate(BaseModel):
    """Schema used to update only the provided fields."""

    formation_id: int | None = Field(default=None, gt=0)
    frais_scolarite: Decimal | None = Field(default=None, ge=0)
    devise: str | None = Field(default=None, min_length=3, max_length=3)
    modalites_paiement: str | None = None
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


class TarifResponse(TarifBase):
    """Schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
