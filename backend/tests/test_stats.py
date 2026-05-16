from models import Summary


def _make_summary(**kw):
    base = dict(
        title="t",
        youtube_url="https://youtu.be/x",
        youtube_id="x",
        language="fr",
        summary_short="s",
        summary_long="l",
        key_points=[],
        sections=[],
        tags=[],
        duration_read=5,
    )
    base.update(kw)
    return Summary(**base)


def test_stats_read_minutes_and_tags(client, db_session):
    db_session.add(_make_summary(duration_read=4, tags=["ia", "tech"]))
    db_session.add(_make_summary(duration_read=6, tags=["tech", "veille"]))
    db_session.commit()

    resp = client.get("/stats/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_summaries"] == 2
    assert data["total_read_minutes"] == 10
    assert data["total_tags"] == 3  # ia, tech, veille (distincts)


def test_stats_empty(client):
    resp = client.get("/stats/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_summaries"] == 0
    assert data["total_read_minutes"] == 0
    assert data["total_tags"] == 0
