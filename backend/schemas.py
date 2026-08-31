from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


# ── Prompt ───────────────────────────────────────────────────────────────────

class PromptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    is_default: bool = False


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    is_default: Optional[bool] = None


class PromptOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    system_prompt: str
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Theme ────────────────────────────────────────────────────────────────────

class ThemeCreate(BaseModel):
    name: str
    color: str = "#6366f1"
    icon: Optional[str] = None


class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ThemeOut(BaseModel):
    id: int
    name: str
    color: str
    icon: Optional[str]
    created_at: datetime
    summary_count: int = 0

    model_config = {"from_attributes": True}


# ── Summary ──────────────────────────────────────────────────────────────────

class Section(BaseModel):
    title: str
    content: str


class SummarizeRequest(BaseModel):
    url: str
    language: str = "fr"
    theme_id: Optional[int] = None
    prompt_id: Optional[int] = None
    tags: list[str] = []

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        if "youtube.com/watch" not in v and "youtu.be/" not in v and "youtube.com/shorts" not in v and "youtube.com/embed" not in v:
            raise ValueError("URL invalide — doit être une URL YouTube")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        allowed = {"fr", "en", "es", "de", "it", "pt", "ja", "zh"}
        if v not in allowed:
            raise ValueError(f"Langue non supportée. Valeurs acceptées : {allowed}")
        return v


class SummaryOut(BaseModel):
    id: int
    title: str
    youtube_url: str
    youtube_id: str
    language: str
    transcript: Optional[str]
    summary_short: str
    summary_long: str
    key_points: list[str]
    sections: list[Section]
    tags: list[str]
    duration_read: int
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost_usd: Optional[float]
    feedback: Optional[int]
    theme_id: Optional[int]
    theme: Optional[ThemeOut]
    prompt_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryListItem(BaseModel):
    id: int
    title: str
    youtube_url: str
    youtube_id: str
    language: str
    summary_short: str
    key_points: list[str]
    tags: list[str]
    duration_read: int
    feedback: Optional[int] = None
    cost_usd: Optional[float]
    theme_id: Optional[int]
    theme: Optional[ThemeOut]
    prompt_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryUpdate(BaseModel):
    theme_id: Optional[int] = None
    tags: Optional[list[str]] = None
    feedback: Optional[int] = None

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (-1, 1):
            raise ValueError("feedback doit valoir 1, -1 ou null")
        return v


# ── Import ───────────────────────────────────────────────────────────────────

class ImportPreviewItem(BaseModel):
    url: str
    video_id: str = ""
    title: str = ""
    already_imported: bool = False
    error: Optional[str] = None


class ImportPreviewResult(BaseModel):
    items: list[ImportPreviewItem]


# ── Stats ─────────────────────────────────────────────────────────────────────

class StatsOut(BaseModel):
    total_summaries: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_read_minutes: int
    total_tags: int


# ── Search ───────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    items: list[SummaryListItem]
    total: int


class TagCount(BaseModel):
    name: str
    count: int
