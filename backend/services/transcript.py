import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname in ("youtu.be",):
        return parsed.path.lstrip("/")
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
        # shorts / embed
        match = re.search(r"/(shorts|embed)/([^/?]+)", parsed.path)
        if match:
            return match.group(2)
    raise ValueError(f"Impossible d'extraire l'ID vidéo depuis : {url}")


async def fetch_transcript(url: str) -> dict:
    video_id = extract_video_id(url)
    try:
        api = YouTubeTranscriptApi()
        # Priorité : FR > EN > toute autre langue disponible
        try:
            fetched = api.fetch(video_id, languages=["fr", "en"])
        except Exception:
            transcript_list = api.list(video_id)
            transcript = next(iter(transcript_list))
            fetched = transcript.fetch()

        full_text = " ".join(s.text for s in fetched)

    except TranscriptsDisabled:
        raise ValueError("Les sous-titres sont désactivés pour cette vidéo.")
    except NoTranscriptFound:
        raise ValueError("Aucun transcript disponible pour cette vidéo.")

    # Titre : on s'appuie sur l'API publique oEmbed (pas de clé requise)
    import httpx
    title = f"Vidéo YouTube ({video_id})"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://www.youtube.com/oembed",
                params={"url": url, "format": "json"},
            )
            if resp.status_code == 200:
                title = resp.json().get("title", title)
    except Exception:
        pass

    return {"video_id": video_id, "title": title, "transcript": full_text}
