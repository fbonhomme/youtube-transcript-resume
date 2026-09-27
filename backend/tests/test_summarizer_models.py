import json

import anthropic
import httpx
import pytest

from services import llm_models, summarizer
from services.summarizer import SummaryGenerationError, anthropic_cost, generate_summary

_OPENROUTER = "google/gemini-3.1-flash-lite"
_URL = "https://www.youtube.com/watch?v=abc"
_RESULT = {
    "summary_short": "court",
    "summary_long": "long",
    "key_points": ["a", "b"],
    "sections": [{"title": "S", "content": "C"}],
    "duration_read": 4,
    "tags": ["ia", "ia", "docker"],
}


@pytest.fixture
def openrouter(monkeypatch):
    """Simule OpenRouter ; `reply` fixe la réponse, `seen` capture la requête."""
    monkeypatch.setattr(summarizer.settings, "openrouter_api_key", "test-or-key")
    state = {"reply": httpx.Response(200, json={}), "seen": None}

    def handler(request: httpx.Request) -> httpx.Response:
        state["seen"] = request
        return state["reply"]

    monkeypatch.setattr(summarizer, "_openrouter_transport", httpx.MockTransport(handler))
    return state


def _chat_reply(content: str, cost: float = 0.00042) -> httpx.Response:
    return httpx.Response(200, json={
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 300, "cost": cost},
    })


def test_anthropic_cost_uses_opus_4_7_pricing():
    assert anthropic_cost(1_000_000, 0, 0, 0) == pytest.approx(5.0)
    assert anthropic_cost(0, 1_000_000, 0, 0) == pytest.approx(25.0)
    assert anthropic_cost(0, 0, 1_000_000, 0) == pytest.approx(6.25)
    assert anthropic_cost(0, 0, 0, 1_000_000) == pytest.approx(0.50)


@pytest.mark.anyio
async def test_openrouter_generation(openrouter):
    openrouter["reply"] = _chat_reply(json.dumps(_RESULT))
    data, usage = await generate_summary("transcript", "Titre", model=_OPENROUTER)

    assert data["summary_short"] == "court"
    assert data["tags"] == ["ia", "docker"]
    assert usage == {"input_tokens": 1200, "output_tokens": 300, "cost_usd": 0.00042}

    req = openrouter["seen"]
    assert str(req.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer test-or-key"
    body = json.loads(req.read())
    assert body["model"] == _OPENROUTER
    assert body["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert "Titre" in body["messages"][1]["content"]


@pytest.mark.anyio
async def test_openrouter_fenced_json_is_accepted(openrouter):
    openrouter["reply"] = _chat_reply("```json\n" + json.dumps(_RESULT) + "\n```")
    data, _ = await generate_summary("t", "T", model=_OPENROUTER)
    assert data["duration_read"] == 4


@pytest.mark.anyio
async def test_openrouter_invalid_json_raises(openrouter):
    openrouter["reply"] = _chat_reply("Désolé, je ne peux pas résumer cette vidéo.")
    with pytest.raises(SummaryGenerationError, match="Gemini 3.1 Flash Lite a renvoyé une réponse qui n'est pas du JSON valide"):
        await generate_summary("t", "T", model=_OPENROUTER)


@pytest.mark.anyio
async def test_openrouter_non_object_json_raises(openrouter):
    openrouter["reply"] = _chat_reply("[1, 2, 3]")
    with pytest.raises(SummaryGenerationError, match="pas du JSON valide"):
        await generate_summary("t", "T", model=_OPENROUTER)


@pytest.mark.anyio
async def test_openrouter_http_error_raises_with_message(openrouter):
    openrouter["reply"] = httpx.Response(402, json={"error": {"message": "Insufficient credits"}})
    with pytest.raises(SummaryGenerationError, match=r"\(402\).*Insufficient credits"):
        await generate_summary("t", "T", model=_OPENROUTER)


@pytest.mark.anyio
async def test_openrouter_network_error_raises(monkeypatch):
    monkeypatch.setattr(summarizer.settings, "openrouter_api_key", "test-or-key")

    def handler(request):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(summarizer, "_openrouter_transport", httpx.MockTransport(handler))
    with pytest.raises(SummaryGenerationError, match="OpenRouter injoignable"):
        await generate_summary("t", "T", model=_OPENROUTER)


@pytest.mark.anyio
async def test_openrouter_malformed_body_raises(openrouter):
    openrouter["reply"] = httpx.Response(200, json={"unexpected": True})
    with pytest.raises(SummaryGenerationError, match="réponse inattendue"):
        await generate_summary("t", "T", model=_OPENROUTER)


@pytest.mark.anyio
async def test_anthropic_api_error_raises(monkeypatch):
    def raise_stream(**kwargs):
        raise anthropic.APIConnectionError(
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        )

    monkeypatch.setattr(summarizer._client.messages, "stream", raise_stream)
    with pytest.raises(SummaryGenerationError, match="Anthropic a renvoyé une erreur"):
        await generate_summary("t", "T")


# ── Route ────────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_transcript(monkeypatch):
    async def fake(url):
        return {"transcript": "blabla", "title": "Vidéo", "video_id": "abc"}

    monkeypatch.setattr("routers.summaries.fetch_transcript", fake)


def _fake_generate(monkeypatch, exc: Exception | None = None):
    calls = []

    async def fake(**kw):
        calls.append(kw)
        if exc:
            raise exc
        return (
            {k: _RESULT[k] for k in ("summary_short", "summary_long", "key_points", "sections", "duration_read")}
            | {"tags": ["ia"]},
            {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.001},
        )

    monkeypatch.setattr("routers.summaries.generate_summary", fake)
    return calls


def test_summarize_passes_and_stores_model(client, fake_transcript, monkeypatch):
    monkeypatch.setattr(llm_models.settings, "openrouter_api_key", "test-or-key")
    calls = _fake_generate(monkeypatch)
    r = client.post("/summaries/", json={"url": _URL, "model": _OPENROUTER})
    assert r.status_code == 201
    assert r.json()["model"] == _OPENROUTER
    assert calls[0]["model"] == _OPENROUTER


def test_summarize_defaults_to_opus(client, fake_transcript, monkeypatch):
    calls = _fake_generate(monkeypatch)
    r = client.post("/summaries/", json={"url": _URL})
    assert r.status_code == 201
    assert r.json()["model"] == llm_models.DEFAULT_MODEL
    assert calls[0]["model"] == llm_models.DEFAULT_MODEL


def test_summarize_generation_error_returns_502(client, fake_transcript, monkeypatch):
    monkeypatch.setattr(llm_models.settings, "openrouter_api_key", "test-or-key")
    _fake_generate(monkeypatch, SummaryGenerationError("OpenRouter a refusé la requête (402) : Insufficient credits"))
    r = client.post("/summaries/", json={"url": _URL, "model": _OPENROUTER})
    assert r.status_code == 502
    assert "402" in r.json()["detail"]
