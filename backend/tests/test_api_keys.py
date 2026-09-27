import pytest
from cryptography.fernet import Fernet

from models import AppSetting
from services import api_keys
from services.api_keys import EncryptionNotConfigured


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", Fernet.generate_key().decode())


@pytest.fixture
def env_keys(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "anthropic_api_key", "")
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", "sk-or-env-0000000000001111")
    monkeypatch.setattr(api_keys.settings, "ai_gateway_api_key", "")


def test_providers():
    assert [p.id for p in api_keys.PROVIDERS] == ["anthropic", "openrouter", "ai_gateway"]
    assert api_keys.get_provider("openrouter").env_var == "openrouter_api_key"
    assert api_keys.get_provider("nope") is None


def test_mask():
    assert api_keys.mask("sk-or-v1-abcdefghijkl1234") == "sk-or-…1234"
    assert api_keys.mask("short") == "••••"


def test_falls_back_to_env(env_keys):
    assert api_keys.get_api_key("openrouter") == "sk-or-env-0000000000001111"
    assert api_keys.get_api_key("anthropic") == ""
    assert api_keys.key_status("openrouter") == {
        "provider": "openrouter",
        "label": "OpenRouter (modèles et Jev)",
        "source": "env",
        "masked": "sk-or-…1111",
        "unreadable": False,
    }
    assert api_keys.key_status("anthropic")["source"] == "none"
    assert api_keys.key_status("anthropic")["masked"] is None


def test_set_overrides_env_and_is_encrypted(env_keys, secret, db_session):
    api_keys.set_api_key("openrouter", "sk-or-ui-9999999999992222")

    assert api_keys.get_api_key("openrouter") == "sk-or-ui-9999999999992222"
    assert api_keys.key_status("openrouter")["source"] == "interface"
    row = db_session.get(AppSetting, "api_key.openrouter")
    assert row is not None
    assert "sk-or-ui" not in row.value


def test_set_twice_replaces(env_keys, secret):
    api_keys.set_api_key("anthropic", "sk-ant-first-000000000000")
    api_keys.set_api_key("anthropic", "sk-ant-second-00000000000")
    assert api_keys.get_api_key("anthropic") == "sk-ant-second-00000000000"


def test_delete_falls_back_to_env(env_keys, secret):
    api_keys.set_api_key("openrouter", "sk-or-ui-9999999999992222")
    api_keys.delete_api_key("openrouter")
    assert api_keys.get_api_key("openrouter") == "sk-or-env-0000000000001111"
    api_keys.delete_api_key("openrouter")  # idempotent


def test_set_without_secret_raises(env_keys, monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", "")
    assert api_keys.encryption_ready() is False
    with pytest.raises(EncryptionNotConfigured):
        api_keys.set_api_key("openrouter", "sk-or-ui-9999999999992222")


def test_invalid_secret_is_not_ready(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", "pas-une-cle-fernet")
    assert api_keys.encryption_ready() is False


def test_changed_secret_marks_unreadable_and_falls_back(env_keys, secret, monkeypatch):
    api_keys.set_api_key("openrouter", "sk-or-ui-9999999999992222")
    monkeypatch.setattr(api_keys.settings, "app_secret_key", Fernet.generate_key().decode())

    assert api_keys.get_api_key("openrouter") == "sk-or-env-0000000000001111"
    status = api_keys.key_status("openrouter")
    assert status["unreadable"] is True
    assert status["source"] == "env"
