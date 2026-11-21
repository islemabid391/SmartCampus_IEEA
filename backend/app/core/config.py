from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartCampus AI API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartcampus"

    # --- Sessions visiteurs (conversation sans compte) ---
    session_ttl_minutes: int = 120          # durÃ©e de validitÃ© d'une session
    session_max_messages: int = 50          # messages "user" max par session
    session_max_conversations: int = 3      # conversations max par session
    
    # --- Authentification ---
    jwt_secret_key: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- Mémoire temporaire des conversations ---
    memoire_ttl_minutes: int = 60           # durée de vie d'un message (plafonnée par la session)
    memoire_max_messages_stockes: int = 100  # messages gardés par conversation
    memoire_fenetre_messages: int = 10      # derniers messages donnés à l'IA
    memoire_max_caracteres: int = 2000      # taille max d'un message conservé

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()