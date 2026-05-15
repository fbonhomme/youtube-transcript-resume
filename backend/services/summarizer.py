import json
import re

import anthropic

from config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

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

# Claude Opus 4.7 pricing (USD per million tokens)
_PRICE = {
    "input": 15.0,
    "output": 75.0,
    "cache_write": 18.75,
    "cache_read": 1.50,
}


def get_default_system_prompt() -> str:
    return _SYSTEM_PROMPT


async def generate_summary(
    transcript: str,
    title: str,
    language: str = "fr",
    system_prompt: str | None = None,
) -> tuple[dict, dict]:
    effective_prompt = system_prompt if system_prompt is not None else _SYSTEM_PROMPT
    lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    user_message = (
        f"Video title: {title}\n\n"
        f"Language instruction: {lang_instruction}\n\n"
        f"Transcript:\n{transcript}"
    )

    full_text = ""
    async with _client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": effective_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            full_text += text
        final_msg = await stream.get_final_message()

    usage = final_msg.usage
    input_tok = getattr(usage, "input_tokens", 0) or 0
    output_tok = getattr(usage, "output_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    cost_usd = (
        input_tok * _PRICE["input"] / 1_000_000
        + output_tok * _PRICE["output"] / 1_000_000
        + cache_write * _PRICE["cache_write"] / 1_000_000
        + cache_read * _PRICE["cache_read"] / 1_000_000
    )

    usage_data = {
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "cost_usd": round(cost_usd, 6),
    }

    json_str = full_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", json_str)
    if match:
        json_str = match.group(1)

    result = json.loads(json_str)

    summary_data = {
        "summary_short": str(result.get("summary_short", "")),
        "summary_long": str(result.get("summary_long", "")),
        "key_points": [str(p) for p in result.get("key_points", [])],
        "sections": [
            {"title": str(s.get("title", "")), "content": str(s.get("content", ""))}
            for s in result.get("sections", [])
        ],
        "duration_read": int(result.get("duration_read", 5)),
    }

    return summary_data, usage_data
