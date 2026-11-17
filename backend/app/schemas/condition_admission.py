
from pydantic import BaseModel, ConfigDict, Field


class ConditionAdmissionBase(BaseModel):
    formation_id: int = Field(gt=0)
    description: str = Field(min_length=1)
    niveau_requis: str | None = None
    documents_requis: str | None = None


class ConditionAdmissionCreate(ConditionAdmissionBase):
    pass


class ConditionAdmissionUpdate(BaseModel):
    formation_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1)
    niveau_requis: str | None = None
    documents_requis: str | None = None


class ConditionAdmissionResponse(ConditionAdmissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
