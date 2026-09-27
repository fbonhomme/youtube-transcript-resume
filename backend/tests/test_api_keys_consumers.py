import json

import httpx
import pytest
from cryptography.fernet import Fernet

from services import api_keys, evaluator, llm_models, summarizer


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(api_keys.settings, "anthropic_api_key", "sk-ant-env-000000000000")
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", "")
    monkeypatch.setattr(api_keys.settings, "ai_gateway_api_key", "")


def test_model_availability_follows_ui_key(secret):
    gemini = llm_models.get_model("google/gemini-3.1-flash-lite")
    assert llm_models.is_available(gemini) is False
    api_keys.set_api_key("openrouter", "sk-or-ui-000000000000")
    assert llm_models.is_available(gemini) is True


def test_jev_uses_ui_openrouter_key(secret):
    assert evaluator.is_enabled() is False
    api_keys.set_api_key("openrouter", "sk-or-ui-000000000000")
    assert evaluator._provider() == (
        evaluator.OPENROUTER_URL, evaluator.OPENROUTER_MODEL, "sk-or-ui-000000000000"
    )


def test_anthropic_client_follows_key_change(secret):
    first = summarizer._anthropic_client()
    assert first.api_key == "sk-ant-env-000000000000"
    assert summarizer._anthropic_client() is first  # réutilisé tant que la clé ne change pas
    api_keys.set_api_key("anthropic", "sk-ant-ui-111111111111")
    second = summarizer._anthropic_client()
    assert second.api_key == "sk-ant-ui-111111111111"


@pytest.mark.anyio
async def test_openrouter_generation_uses_ui_key(secret, monkeypatch):
    api_keys.set_api_key("openrouter", "sk-or-ui-000000000000")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps({"summary_short": "c", "summary_long": "l"})}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.0001},
        })

    monkeypatch.setattr(summarizer, "_openrouter_transport", httpx.MockTransport(handler))
    await summarizer.generate_summary("t", "T", model="google/gemini-3.1-flash-lite")
    assert seen["auth"] == "Bearer sk-or-ui-000000000000"
