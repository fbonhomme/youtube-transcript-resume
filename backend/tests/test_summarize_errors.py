async def _raise_disabled(url):
    raise ValueError("Les sous-titres sont désactivés pour cette vidéo.")


async def _raise_bad_id(url):
    raise ValueError("Impossible d'extraire l'ID vidéo depuis : x")


def test_transcript_disabled_returns_422(client, monkeypatch):
    monkeypatch.setattr("routers.summaries.fetch_transcript", _raise_disabled)
    r = client.post(
        "/summaries/",
        json={"url": "https://www.youtube.com/watch?v=NBS4-sBClZU"},
    )
    assert r.status_code == 422
    assert "sous-titres" in r.json()["detail"].lower()


def test_bad_video_id_returns_422(client, monkeypatch):
    monkeypatch.setattr("routers.summaries.fetch_transcript", _raise_bad_id)
    r = client.post(
        "/summaries/",
        json={"url": "https://www.youtube.com/watch?v=zzz"},
    )
    assert r.status_code == 422
    assert "vidéo" in r.json()["detail"].lower()
