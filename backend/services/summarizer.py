import json
import re

import anthropic
import httpx

from services.api_keys import get_api_key
from services.llm_models import DEFAULT_MODEL, get_model

_anthropic_clients: dict[str, anthropic.AsyncAnthropic] = {}


def _anthropic_client() -> anthropic.AsyncAnthropic:
    """Client Anthropic pour la clé en vigueur (recréé si la clé change)."""
    key = get_api_key("anthropic")
    client = _anthropic_clients.get(key)
    if client is None:
        _anthropic_clients.clear()
        client = _anthropic_clients[key] = anthropic.AsyncAnthropic(api_key=key)
    return client

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_MAX_TOKENS = 16000

# Transport httpx injectable pour les tests.
_openrouter_transport: httpx.AsyncBaseTransport | None = None

# Claude Opus 4.7 en direct (USD par million de tokens). Écriture cache =
# 1,25 × entrée, lecture cache = 0,1 × entrée.
_ANTHROPIC_PRICE = {
    "input": 5.0,
    "output": 25.0,
    "cache_write": 6.25,
    "cache_read": 0.50,
}


class SummaryGenerationError(Exception):
    """Échec de génération dont le message peut être montré à l'utilisateur."""


def anthropic_cost(input_tokens: int, output_tokens: int, cache_write: int, cache_read: int) -> float:
    return (
        input_tokens * _ANTHROPIC_PRICE["input"]
        + output_tokens * _ANTHROPIC_PRICE["output"]
        + cache_write * _ANTHROPIC_PRICE["cache_write"]
        + cache_read * _ANTHROPIC_PRICE["cache_read"]
    ) / 1_000_000


_SYSTEM_PROMPT = """\
You are an expert at synthesizing YouTube video content from transcripts.
Given a transcript and video title, produce a structured JSON summary.

Your response MUST be valid JSON matching exactly this schema:
{
  "summary_short": "<2-3 sentence overview>",
  "summary_long": "<comprehensive 5-10 paragraph summary>",
  "key_points": ["<point 1>", "<point 2>", ...],
  "sections": [
    {"title": "<section title>", "content": "<section content>"},
    ...
  ],
  "duration_read": <estimated minutes to read as integer>
}

Rules:
- summary_short: 2-3 sentences, captures the essence
- summary_long: thorough coverage of all major topics discussed
- key_points: 5-10 bullet points, most important takeaways
- sections: 3-7 thematic sections with meaningful titles
- duration_read: integer, realistic reading time in minutes (1 min ≈ 200 words)
- Respond ONLY with the JSON object, no markdown fences, no preamble
"""

_TAGS_RULE = """

En plus des champs ci-dessus, ajoute un champ "tags" à l'objet JSON : une liste \
de 2 à 5 tags courts (1 à 3 mots) identifiant les technologies, outils, produits \
ou thèmes clés abordés dans la vidéo. Réutilise en priorité un tag déjà existant \
dans la bibliothèque (fourni séparément dans le message utilisateur) si le sujet \
correspond, plutôt que d'en créer un proche en sens. Si aucun tag existant ne \
convient, crée-en un nouveau, court et cohérent avec le style existant (noms \
d'outils/produits tels quels, catégories génériques en français)."""

_LANGUAGE_INSTRUCTIONS = {
    "fr": "Write the entire summary in French.",
    "en": "Write the entire summary in English.",
    "es": "Write the entire summary in Spanish.",
    "de": "Write the entire summary in German.",
    "it": "Write the entire summary in Italian.",
    "pt": "Write the entire summary in Portuguese.",
    "ja": "Write the entire summary in Japanese.",
    "zh": "Write the entire summary in Chinese (Simplified).",
}


def get_default_system_prompt() -> str:
    return _SYSTEM_PROMPT


async def _call_anthropic(model_id: str, system_prompt: str, user_message: str) -> tuple[str, dict]:
    full_text = ""
    try:
        async with _anthropic_client().messages.stream(
            model=model_id,
            max_tokens=_MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for text in stream.text_stream:
                full_text += text
            final_msg = await stream.get_final_message()
    except anthropic.APIError as exc:
        raise SummaryGenerationError(f"Anthropic a renvoyé une erreur : {exc}") from exc

    usage = final_msg.usage
    input_tok = getattr(usage, "input_tokens", 0) or 0
    output_tok = getattr(usage, "output_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    return full_text, {
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "cost_usd": round(anthropic_cost(input_tok, output_tok, cache_write, cache_read), 6),
    }


def _openrouter_error(resp: httpx.Response) -> str:
    try:
        return resp.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return resp.text[:200]


async def _call_openrouter(model_id: str, system_prompt: str, user_message: str) -> tuple[str, dict]:
    try:
        async with httpx.AsyncClient(timeout=300, transport=_openrouter_transport) as client:
            resp = await client.post(
                OPENROUTER_CHAT_URL,
                headers={"Authorization": f"Bearer {get_api_key('openrouter')}"},
                json={
                    "model": model_id,
                    "max_tokens": _MAX_TOKENS,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                },
            )
    except httpx.HTTPError as exc:
        # Ne jamais inclure le texte de l'exception : il peut contenir la clé
        # API en clair (ex. LocalProtocolError sur un en-tête Authorization
        # malformé). Seul le type d'erreur est reporté, comme dans key_check.py.
        raise SummaryGenerationError(f"OpenRouter injoignable : {type(exc).__name__}") from exc
    if resp.status_code != 200:
        raise SummaryGenerationError(
            f"OpenRouter a refusé la requête ({resp.status_code}) : {_openrouter_error(resp)}"
        )
    try:
        data = resp.json()
        choice = data["choices"][0]
        content = choice["message"].get("content")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise SummaryGenerationError("OpenRouter a renvoyé une réponse inattendue") from exc
    if choice.get("finish_reason") == "length":
        raise SummaryGenerationError(
            f"Réponse tronquée : la limite de {_MAX_TOKENS} tokens a été atteinte"
        )
    if not content:
        raise SummaryGenerationError("OpenRouter a renvoyé une réponse vide")
    usage = data.get("usage") or {}
    cost = usage.get("cost")
    return content, {
        "input_tokens": usage.get("prompt_tokens", 0) or 0,
        "output_tokens": usage.get("completion_tokens", 0) or 0,
        "cost_usd": round(float(cost), 6) if cost is not None else None,
    }


def _parse_json(text: str) -> dict:
    stripped = text.strip()
    try:
        result = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", stripped)
        if not match:
            raise
        result = json.loads(match.group(1))
    if not isinstance(result, dict):
        raise ValueError("objet JSON attendu")
    return result


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _clean_str_list(value: object) -> list[str]:
    return [s for s in (str(v).strip() for v in _as_list(value)) if s]


def _normalize_sections(value: object) -> list[dict]:
    sections = []
    for item in _as_list(value):
        if not isinstance(item, dict):
            continue
        sections.append({"title": str(item.get("title", "")), "content": str(item.get("content", ""))})
    return sections


def _normalize_duration(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 5


async def generate_summary(
    transcript: str,
    title: str,
    language: str = "fr",
    system_prompt: str | None = None,
    existing_tags: list[str] | None = None,
    model: str = DEFAULT_MODEL,
) -> tuple[dict, dict]:
    llm = get_model(model)
    if llm is None:
        raise ValueError(f"Modèle inconnu : {model}")

    base_prompt = system_prompt if system_prompt is not None else _SYSTEM_PROMPT
    effective_prompt = base_prompt + _TAGS_RULE
    lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    tags_hint = ", ".join(sorted(existing_tags)) if existing_tags else "(aucun pour le moment)"
    user_message = (
        f"Video title: {title}\n\n"
        f"Language instruction: {lang_instruction}\n\n"
        f"Tags déjà existants dans la bibliothèque : {tags_hint}\n\n"
        f"Transcript:\n{transcript}"
    )

    call = _call_openrouter if llm.provider == "openrouter" else _call_anthropic
    full_text, usage_data = await call(llm.id, effective_prompt, user_message)

    try:
        result = _parse_json(full_text)
    except ValueError as exc:  # json.JSONDecodeError hérite de ValueError
        raise SummaryGenerationError(
            f"{llm.label} a renvoyé une réponse qui n'est pas du JSON valide"
        ) from exc

    raw_tags = _clean_str_list(result.get("tags"))
    tags = list(dict.fromkeys(raw_tags))[:5]

    summary_short = str(result.get("summary_short", "")).strip()
    summary_long = str(result.get("summary_long", "")).strip()
    if not summary_short or not summary_long:
        raise SummaryGenerationError(f"{llm.label} n'a pas respecté le format attendu")

    summary_data = {
        "summary_short": summary_short,
        "summary_long": summary_long,
        "key_points": _clean_str_list(result.get("key_points")),
        "sections": _normalize_sections(result.get("sections")),
        "duration_read": _normalize_duration(result.get("duration_read", 5)),
        "tags": tags,
    }

    return summary_data, usage_data
