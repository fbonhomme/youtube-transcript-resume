"""Clés API des fournisseurs.

Clé en vigueur = clé saisie dans l'administration (chiffrée en base avec
APP_SECRET_KEY), sinon variable du .env, sinon "".
"""
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

from config import settings
from database import SessionLocal
from models import AppSetting


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    env_var: str  # attribut de Settings (= variable du .env en minuscules)


PROVIDERS: tuple[Provider, ...] = (
    Provider("anthropic", "Anthropic (Claude en direct)", "anthropic_api_key"),
    Provider("openrouter", "OpenRouter (modèles et Jev)", "openrouter_api_key"),
    Provider("ai_gateway", "Vercel AI Gateway (Jev, secours)", "ai_gateway_api_key"),
)
_BY_ID = {p.id: p for p in PROVIDERS}

# Remplacé par la base de test dans tests/conftest.py.
_session_factory = SessionLocal


class EncryptionNotConfigured(Exception):
    """APP_SECRET_KEY absente ou invalide : impossible d'enregistrer une clé."""


def get_provider(provider_id: str) -> Provider | None:
    return _BY_ID.get(provider_id)


def _fernet() -> Fernet | None:
    if not settings.app_secret_key:
        return None
    try:
        return Fernet(settings.app_secret_key.encode())
    except ValueError:
        return None


def encryption_ready() -> bool:
    return _fernet() is not None


def _row_key(provider: Provider) -> str:
    return f"api_key.{provider.id}"


def _stored(provider: Provider) -> tuple[str | None, bool]:
    """(clé saisie déchiffrée ou None, clé stockée mais illisible)."""
    with _session_factory() as db:
        row = db.get(AppSetting, _row_key(provider))
        token = row.value if row else None
    if token is None:
        return None, False
    fernet = _fernet()
    if fernet is None:
        return None, True
    try:
        return fernet.decrypt(token.encode()).decode(), False
    except InvalidToken:
        return None, True


def get_api_key(provider_id: str) -> str:
    provider = _BY_ID[provider_id]
    stored, _ = _stored(provider)
    return stored or getattr(settings, provider.env_var)


def set_api_key(provider_id: str, value: str) -> None:
    provider = _BY_ID[provider_id]
    fernet = _fernet()
    if fernet is None:
        raise EncryptionNotConfigured()
    token = fernet.encrypt(value.encode()).decode()
    with _session_factory() as db:
        row = db.get(AppSetting, _row_key(provider))
        if row is None:
            db.add(AppSetting(key=_row_key(provider), value=token))
        else:
            row.value = token
        db.commit()


def delete_api_key(provider_id: str) -> None:
    provider = _BY_ID[provider_id]
    with _session_factory() as db:
        row = db.get(AppSetting, _row_key(provider))
        if row is not None:
            db.delete(row)
            db.commit()


def mask(value: str) -> str:
    return f"{value[:6]}…{value[-4:]}" if len(value) > 12 else "••••"


def key_status(provider_id: str) -> dict:
    provider = _BY_ID[provider_id]
    stored, unreadable = _stored(provider)
    env_value = getattr(settings, provider.env_var)
    if stored:
        source, value = "interface", stored
    elif env_value:
        source, value = "env", env_value
    else:
        source, value = "none", ""
    return {
        "provider": provider.id,
        "label": provider.label,
        "source": source,
        "masked": mask(value) if value else None,
        "unreadable": unreadable,
    }
