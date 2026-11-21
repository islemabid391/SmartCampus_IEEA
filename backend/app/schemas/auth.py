from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=8, max_length=72)
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    telephone: str | None = Field(default=None, max_length=30)
    consentement_rgpd: bool


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    mot_de_passe: str = Field(max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str
    nom: str
    prenom: str
    etablissement_id: int | None