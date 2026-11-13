from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartCampus AI API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartcampus"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()