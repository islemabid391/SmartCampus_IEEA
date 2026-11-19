from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    langue_detectee: str | None
    date_creation: datetime


class MessageCreate(BaseModel):
    contenu: str = Field(min_length=1, max_length=5000)
    langue: str | None = Field(default=None, max_length=20)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    contenu: str
    langue: str | None
    date_creation: datetime
    date_expiration: datetime | None


class MemoireResponse(BaseModel):
    informations: dict
    infos_manquantes: list[str]