from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    # Jev (classement/notation) : OpenRouter prioritaire, sinon Vercel AI
    # Gateway. Aucune des deux clés = Jev désactivé.
    openrouter_api_key: str = ""
    ai_gateway_api_key: str = ""
    database_url: str = "sqlite:///./yt_summaries.db"

    model_config = {"env_file": ".env"}


settings = Settings()
