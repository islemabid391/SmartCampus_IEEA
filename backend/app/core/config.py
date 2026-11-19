from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartCampus AI API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartcampus"

    # --- Sessions visiteurs (conversation sans compte) ---
    session_ttl_minutes: int = 120          # durée de validité d'une session
    session_max_messages: int = 50          # messages "user" max par session
    session_max_conversations: int = 3      # conversations max par session

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()