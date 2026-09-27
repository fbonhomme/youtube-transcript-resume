import httpx
import pytest

from models import Summary, Theme
from services import api_keys, evaluator

_SCORES = {"densite": 2.5, "niveau": 1.0, "actionnable": 3.0, "perennite": 0.4}


def _make_summary(**kw):
    base = dict(
        title="t",
        youtube_url="https://youtu.be/x",
        youtube_id="x",
        language="fr",
        summary_short="s",
        summary_long="l",
        key_points=["p1"],
        sections=[],
        tags=["ia"],
        duration_read=5,
    )
    base.update(kw)
    return Summary(**base)


def _answers(choice: str | None, prob: float = 0.9, scores: dict = _SCORES) -> dict:
    answers = {k: {"type": "score", "score": v} for k, v in scores.items()}
    if choice is not None:
        answers["theme"] = {"type": "choice", "choice": choice, "probabilities": {choice: prob}}
    return answers


@pytest.fixture
def jev_disabled(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", "")
    monkeypatch.setattr(api_keys.settings, "ai_gateway_api_key", "")


@pytest.fixture
def jev_enabled(jev_disabled, monkeypatch):
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", "test-openrouter-key")


def _fake_evaluate(monkeypatch, answers_or_exc):
    calls = []

    async def fake(state, questions):
        calls.append((state, questions))
        if isinstance(answers_or_exc, Exception):
            raise answers_or_exc
        return answers_or_exc

    monkeypatch.setattr(evaluator, "evaluate", fake)
    return calls


# ── Service ───────────────────────────────────────────────────────────────────

def test_build_questions_uses_theme_descriptions():
    themes = [Theme(id=1, name="Tech", description="Outils de dev"), Theme(id=2, name="Cuisine")]
    q = evaluator.build_questions(themes)
    assert set(q) == {*evaluator.SCORE_CRITERIA, "theme"}
    assert q["theme"]["criteria"] == {
        "t1": "Tech — Outils de dev",
        "t2": "Cuisine",
        "aucun": q["theme"]["criteria"]["aucun"],
    }
    assert all(len(q[k]["criteria"]) == 4 for k in evaluator.SCORE_CRITERIA)


def test_build_questions_without_themes_skips_theme_question():
    assert "theme" not in evaluator.build_questions([])


def test_parse_answers():
    parsed = evaluator.parse_answers(_answers("t7", 0.73))
    assert parsed == {"scores": _SCORES, "theme_id": 7, "theme_confidence": 0.73}
    assert evaluator.parse_answers(_answers("aucun"))["theme_id"] is None


@pytest.mark.parametrize(
    "confidence, theme_id, suggestion_id",
    [(0.92, 3, None), (0.65, None, 3), (0.3, None, None)],
)
def test_apply_analysis_thresholds(confidence, theme_id, suggestion_id):
    s = _make_summary()
    evaluator.apply_analysis(s, {"scores": _SCORES, "theme_id": 3, "theme_confidence": confidence})
    assert s.scores == _SCORES
    assert s.theme_id == theme_id
    assert s.theme_suggestion_id == suggestion_id


def test_apply_analysis_keeps_existing_theme():
    s = _make_summary(theme_id=1)
    evaluator.apply_analysis(s, {"scores": _SCORES, "theme_id": 3, "theme_confidence": 0.99})
    assert s.theme_id == 1
    assert s.theme_suggestion_id is None


@pytest.mark.parametrize(
    "openrouter_key, gateway_key, url, model, key",
    [
        ("or-key", "gw-key", evaluator.OPENROUTER_URL, "typesafe/jev-1.13", "or-key"),
        ("", "gw-key", evaluator.VERCEL_URL, "typesafe-ai/jev", "gw-key"),
    ],
)
@pytest.mark.anyio
async def test_evaluate_calls_configured_provider(
    monkeypatch, openrouter_key, gateway_key, url, model, key
):
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", openrouter_key)
    monkeypatch.setattr(api_keys.settings, "ai_gateway_api_key", gateway_key)
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.read()
        return httpx.Response(200, json={"answers": _answers(None), "usage": {"cost": 0.00002}})

    monkeypatch.setattr(evaluator, "_transport", httpx.MockTransport(handler))
    answers = await evaluator.evaluate("state", {"q": {"type": "score"}})

    assert answers == _answers(None)
    assert seen["url"] == url
    assert seen["auth"] == f"Bearer {key}"
    assert f'"model":"{model}"'.encode() in seen["body"].replace(b" ", b"")


# ── Création d'une synthèse ──────────────────────────────────────────────────

@pytest.fixture
def fake_pipeline(monkeypatch):
    async def fake_transcript(url):
        return {"transcript": "blabla", "title": "Vidéo", "video_id": "abc"}

    async def fake_generate(**kw):
        return (
            {
                "summary_short": "court",
                "summary_long": "long",
                "key_points": ["a"],
                "sections": [],
                "duration_read": 3,
                "tags": ["ia"],
            },
            {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0},
        )

    monkeypatch.setattr("routers.summaries.fetch_transcript", fake_transcript)
    monkeypatch.setattr("routers.summaries.generate_summary", fake_generate)


_URL = "https://www.youtube.com/watch?v=abc"


def test_summarize_auto_classifies(client, db_session, fake_pipeline, jev_enabled, monkeypatch):
    theme = Theme(name="Tech")
    db_session.add(theme)
    db_session.commit()
    _fake_evaluate(monkeypatch, _answers(f"t{theme.id}", 0.95))

    r = client.post("/summaries/", json={"url": _URL})
    assert r.status_code == 201
    body = r.json()
    assert body["theme_id"] == theme.id
    assert body["theme_confidence"] == 0.95
    assert body["scores"] == _SCORES


def test_summarize_survives_jev_failure(client, fake_pipeline, jev_enabled, monkeypatch):
    _fake_evaluate(monkeypatch, RuntimeError("gateway down"))
    r = client.post("/summaries/", json={"url": _URL})
    assert r.status_code == 201
    assert r.json()["scores"] is None


def test_summarize_without_gateway_key_skips_jev(client, fake_pipeline, jev_disabled, monkeypatch):
    calls = _fake_evaluate(monkeypatch, _answers(None))
    r = client.post("/summaries/", json={"url": _URL})
    assert r.status_code == 201
    assert calls == []


# ── Ré-analyse ───────────────────────────────────────────────────────────────

def test_analyze_requires_gateway_key(client, jev_disabled):
    assert client.post("/summaries/analyze").status_code == 503


def test_analyze_library_report(client, db_session, jev_enabled, monkeypatch):
    theme = Theme(name="Tech")
    db_session.add(theme)
    db_session.commit()
    db_session.add_all([_make_summary(), _make_summary(theme_id=theme.id)])
    db_session.commit()
    _fake_evaluate(monkeypatch, _answers(f"t{theme.id}", 0.6))

    r = client.post("/summaries/analyze")
    assert r.status_code == 200
    assert r.json() == {"analyzed": 2, "auto_classified": 0, "suggested": 1, "failed": 0}


def test_analyze_one(client, db_session, jev_enabled, monkeypatch):
    s = _make_summary()
    db_session.add(s)
    db_session.commit()
    _fake_evaluate(monkeypatch, _answers(None))
    r = client.post(f"/summaries/{s.id}/analyze")
    assert r.status_code == 200
    assert r.json()["scores"] == _SCORES


def test_analyze_one_gateway_error_returns_502(client, db_session, jev_enabled, monkeypatch):
    s = _make_summary()
    db_session.add(s)
    db_session.commit()
    _fake_evaluate(monkeypatch, RuntimeError("boom"))
    assert client.post(f"/summaries/{s.id}/analyze").status_code == 502


# ── Suggestion de thème ──────────────────────────────────────────────────────

def test_setting_theme_clears_suggestion(client, db_session):
    theme = Theme(name="Tech")
    db_session.add(theme)
    db_session.commit()
    s = _make_summary(theme_suggestion_id=theme.id, theme_confidence=0.6)
    db_session.add(s)
    db_session.commit()

    r = client.patch(f"/summaries/{s.id}", json={"theme_id": theme.id})
    assert r.json()["theme_id"] == theme.id
    assert r.json()["theme_suggestion_id"] is None
    assert r.json()["theme_confidence"] is None


def test_dismiss_suggestion(client, db_session):
    s = _make_summary(theme_suggestion_id=4, theme_confidence=0.6)
    db_session.add(s)
    db_session.commit()
    r = client.patch(f"/summaries/{s.id}", json={"theme_suggestion_id": None})
    assert r.json()["theme_suggestion_id"] is None


def test_deleting_theme_clears_suggestions(client, db_session):
    theme = Theme(name="Tech")
    db_session.add(theme)
    db_session.commit()
    s = _make_summary(theme_suggestion_id=theme.id, theme_confidence=0.6)
    db_session.add(s)
    db_session.commit()

    assert client.delete(f"/themes/{theme.id}").status_code == 204
    assert client.get(f"/summaries/{s.id}").json()["theme_suggestion_id"] is None


def test_theme_description_roundtrip(client):
    r = client.post("/themes/", json={"name": "Tech", "description": "Outils de dev"})
    assert r.json()["description"] == "Outils de dev"
    r = client.put(f"/themes/{r.json()['id']}", json={"description": "IA et cloud"})
    assert r.json()["description"] == "IA et cloud"


# ── Tri ──────────────────────────────────────────────────────────────────────

def test_search_sort_by_score_puts_unscored_last(client, db_session):
    db_session.add_all([
        _make_summary(title="peu dense", scores={**_SCORES, "densite": 0.5}),
        _make_summary(title="non notée"),
        _make_summary(title="dense", scores={**_SCORES, "densite": 2.9}),
    ])
    db_session.commit()
    r = client.get("/search/", params={"sort": "densite"})
    assert [i["title"] for i in r.json()["items"]] == ["dense", "peu dense", "non notée"]


def test_search_sort_top_includes_feedback(client, db_session):
    db_session.add_all([
        _make_summary(title="bien notée", scores=_SCORES),
        _make_summary(title="aimée", scores=_SCORES, feedback=1),
        _make_summary(title="rejetée", scores=_SCORES, feedback=-1),
    ])
    db_session.commit()
    r = client.get("/search/", params={"sort": "top"})
    assert [i["title"] for i in r.json()["items"]] == ["aimée", "bien notée", "rejetée"]


def test_search_rejects_unknown_sort(client):
    assert client.get("/search/", params={"sort": "nope"}).status_code == 422
