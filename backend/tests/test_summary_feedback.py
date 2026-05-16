from models import Summary


def _seed(db):
    s = Summary(
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
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.id


def test_set_like_then_dislike_then_neutral(client, db_session):
    sid = _seed(db_session)

    r = client.patch(f"/summaries/{sid}", json={"feedback": 1})
    assert r.status_code == 200
    assert r.json()["feedback"] == 1

    r = client.patch(f"/summaries/{sid}", json={"feedback": -1})
    assert r.json()["feedback"] == -1

    r = client.patch(f"/summaries/{sid}", json={"feedback": None})
    assert r.json()["feedback"] is None


def test_feedback_invalid_value_rejected(client, db_session):
    sid = _seed(db_session)
    r = client.patch(f"/summaries/{sid}", json={"feedback": 2})
    assert r.status_code == 422


def test_patch_without_feedback_preserves_it(client, db_session):
    sid = _seed(db_session)
    client.patch(f"/summaries/{sid}", json={"feedback": 1})
    r = client.patch(f"/summaries/{sid}", json={"tags": ["x"]})
    assert r.status_code == 200
    assert r.json()["feedback"] == 1
    assert r.json()["tags"] == ["x"]
