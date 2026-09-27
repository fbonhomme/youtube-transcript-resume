from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Clés des fournisseurs : valeurs par défaut, remplaçables depuis la page
    # Administration (services/api_keys.py).
    anthropic_api_key: str = ""
    # Jev (classement/notation) : OpenRouter prioritaire, sinon Vercel AI
    # Gateway. Aucune des deux clés = Jev désactivé.
    openrouter_api_key: str = ""
    ai_gateway_api_key: str = ""
    # Clé maître Fernet chiffrant les clés saisies dans l'administration.
    app_secret_key: str = ""
    # Docker uniquement : faire confiance à l'en-tête X-Admin-Access posé par
    # le bloc nginx d'administration (port 8080 lié à 127.0.0.1).
    admin_trust_proxy_header: bool = False
    database_url: str = "sqlite:///./yt_summaries.db"

    model_config = {"env_file": ".env"}


settings = Settings()
