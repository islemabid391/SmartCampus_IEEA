from pydantic import SecretStr
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
    candidat_max_messages_jour: int = 100   # questions par jour d'un candidat connecté
    memoire_max_caracteres: int = 2000      # taille max d'un message conservé

    # --- LLM (API compatible OpenAI : Groq, OpenRouter, Ollama...) ---
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-20b"        # modèle retenu en SA-33
    llm_api_key: SecretStr | None = None         # jamais affichée ni journalisée
    llm_timeout_secondes: float = 30.0           # délai maximal d'une requête
    llm_max_tokens: int = 1500                   # recommandation du rapport SA-33
    llm_temperature: float = 0.2
    llm_max_retries: int = 2                     # nouvelles tentatives (timeout, 5xx, réseau)

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()