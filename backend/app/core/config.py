from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://crm:crm@db:5432/crm"
    SECRET_KEY: str = "dev-secret-change-me"
    # OpenRouter (OpenAI-compatible). Set to swap providers/models without code changes.
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"
    OPENROUTER_FALLBACK_MODELS: str = ""  # comma-separated; tried in order on failure
    OPENROUTER_HTTP_REFERER: str = "https://news-crm.local"
    OPENROUTER_APP_TITLE: str = "News CRM"
    AI_REQUEST_TIMEOUT_S: float = 30.0
    CORS_ORIGINS: str = "http://localhost:3000"
    RESEND_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def openrouter_fallback_models(self) -> list[str]:
        return [m.strip() for m in self.OPENROUTER_FALLBACK_MODELS.split(",") if m.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)


settings = Settings()
