"""Catalogue des modèles proposés pour générer les synthèses.

Les prix (USD par million de tokens) sont indicatifs, pour l'interface : le
coût réellement facturé est calculé à la génération (voir summarizer).
Catalogue vérifié le 2026-09-27 : sortie JSON supportée, contexte >= 400k.
"""
from dataclasses import dataclass

from services.api_keys import get_api_key


@dataclass(frozen=True)
class LLMModel:
    id: str
    label: str
    provider: str  # "anthropic" (SDK direct) | "openrouter"
    input_price: float
    output_price: float


DEFAULT_MODEL = "claude-opus-4-7"

MODELS: tuple[LLMModel, ...] = (
    LLMModel("claude-opus-4-7", "Claude Opus 4.7", "anthropic", 5.0, 25.0),
    LLMModel("anthropic/claude-sonnet-5", "Claude Sonnet 5", "openrouter", 2.0, 10.0),
    LLMModel("openai/gpt-5.4-mini", "GPT-5.4 mini", "openrouter", 0.75, 4.5),
    LLMModel("google/gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite", "openrouter", 0.25, 1.5),
    LLMModel("deepseek/deepseek-v4-flash", "DeepSeek V4 Flash", "openrouter", 0.05, 0.09),
)

_BY_ID = {m.id: m for m in MODELS}


def get_model(model_id: str) -> LLMModel | None:
    return _BY_ID.get(model_id)


def is_available(model: LLMModel) -> bool:
    return bool(get_api_key("openrouter" if model.provider == "openrouter" else "anthropic"))
