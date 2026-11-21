from pydantic import BaseModel


class RattachementApercu(BaseModel):
    rattachable: bool
    nb_conversations: int
    nb_messages: int


class RattachementRequest(BaseModel):
    consentement: bool


class RattachementResponse(BaseModel):
    conversations_rattachees: int