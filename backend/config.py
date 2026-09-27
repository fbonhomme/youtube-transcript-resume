from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    # Clé Vercel AI Gateway pour Jev (classement/notation). Vide = Jev désactivé.
    ai_gateway_api_key: str = ""
    database_url: str = "sqlite:///./yt_summaries.db"

    model_config = {"env_file": ".env"}


settings = Settings()
