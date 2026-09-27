import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from services import llm_models

_ANTHROPIC = "claude-opus-4-7"
_OPENROUTER = "google/gemini-3.1-flash-lite"
_URL = "https://www.youtube.com/watch?v=abc"


@pytest.fixture
def openrouter_key(monkeypatch):
    monkeypatch.setattr(llm_models.settings, "openrouter_api_key", "test-or-key")


@pytest.fixture
def no_openrouter_key(monkeypatch):
    monkeypatch.setattr(llm_models.settings, "openrouter_api_key", "")


def test_catalog_default_is_first_and_known():
    assert llm_models.MODELS[0].id == llm_models.DEFAULT_MODEL == _ANTHROPIC
    assert llm_models.get_model(_OPENROUTER).provider == "openrouter"
    assert llm_models.get_model("nope/nope") is None


def test_list_models(client, openrouter_key):
    r = client.get("/models/")
    assert r.status_code == 200
    body = r.json()
    assert [m["id"] for m in body] == [m.id for m in llm_models.MODELS]
    assert body[0] == {
        "id": _ANTHROPIC,
        "label": "Claude Opus 4.7",
        "provider": "anthropic",
        "input_price": 5.0,
        "output_price": 25.0,
        "available": True,
        "is_default": True,
    }
    assert all(m["available"] for m in body)
    assert sum(m["is_default"] for m in body) == 1


def test_list_models_marks_openrouter_unavailable_without_key(client, no_openrouter_key):
    body = {m["id"]: m for m in client.get("/models/").json()}
    assert body[_ANTHROPIC]["available"] is True
    assert body[_OPENROUTER]["available"] is False


def test_summarize_unknown_model_returns_422(client):
    r = client.post("/summaries/", json={"url": _URL, "model": "nope/nope"})
    assert r.status_code == 422
    assert "Modèle inconnu" in r.json()["detail"]


def test_summarize_unavailable_model_returns_422(client, no_openrouter_key):
    r = client.post("/summaries/", json={"url": _URL, "model": _OPENROUTER})
    assert r.status_code == 422
    assert "indisponible" in r.json()["detail"]


def test_migration_backfills_model(tmp_path, monkeypatch):
    db = tmp_path / "m.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db.as_posix()}")
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "0004")
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO summaries"
        " (title, youtube_url, youtube_id, language, summary_short, summary_long,"
        "  key_points, sections, tags, created_at)"
        " VALUES ('t', 'u', 'x', 'fr', 's', 'l', '[]', '[]', '[]', '2026-09-27 00:00:00')"
    )
    con.commit()
    con.close()

    command.upgrade(cfg, "head")

    con = sqlite3.connect(db)
    assert con.execute("SELECT model FROM summaries").fetchone() == (_ANTHROPIC,)
    con.close()
