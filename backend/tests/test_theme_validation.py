from models import Summary, Theme


def _summary(**kw):
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


def _seed(db):
    tech, cuisine = Theme(name="Tech"), Theme(name="Cuisine")
    db.add_all([tech, cuisine])
    db.commit()
    db.add_all([
        _summary(title="classée", theme_id=tech.id),
        _summary(title="suggérée tech", theme_suggestion_id=tech.id, theme_confidence=0.6),
        _summary(title="suggérée cuisine", theme_suggestion_id=cuisine.id, theme_confidence=0.7),
        _summary(title="sans thème"),
    ])
    db.commit()
    return tech, cuisine


def _titles(r):
    return sorted(i["title"] for i in r.json()["items"])


def test_search_filter_pending(client, db_session):
    _seed(db_session)
    r = client.get("/search/", params={"status": "pending"})
    assert _titles(r) == ["suggérée cuisine", "suggérée tech"]
    assert r.json()["total"] == 2


def test_search_filter_unthemed(client, db_session):
    _seed(db_session)
    assert _titles(client.get("/search/", params={"status": "unthemed"})) == ["sans thème"]


def test_search_rejects_unknown_status(client):
    assert client.get("/search/", params={"status": "nope"}).status_code == 422


def test_theme_status_counts(client, db_session):
    _seed(db_session)
    assert client.get("/search/theme-status").json() == {"pending": 2, "unthemed": 1}


def test_accept_all_suggestions(client, db_session):
    tech, cuisine = _seed(db_session)
    r = client.post("/summaries/accept-suggestions")
    assert r.status_code == 200
    assert r.json() == {"accepted": 2}

    by_title = {s.title: s for s in db_session.query(Summary).all()}
    assert by_title["suggérée tech"].theme_id == tech.id
    assert by_title["suggérée cuisine"].theme_id == cuisine.id
    for title in ("suggérée tech", "suggérée cuisine"):
        assert by_title[title].theme_suggestion_id is None
        assert by_title[title].theme_confidence is None
    assert by_title["sans thème"].theme_id is None
    assert client.get("/search/theme-status").json() == {"pending": 0, "unthemed": 1}


def test_accept_all_when_nothing_pending(client):
    assert client.post("/summaries/accept-suggestions").json() == {"accepted": 0}
