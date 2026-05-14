from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, field_validator


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
    tags: list[str] = []

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        if "youtube.com/watch" not in v and "youtu.be/" not in v:
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
    summary_short: str
    summary_long: str
    key_points: list[str]
    sections: list[Section]
    tags: list[str]
    duration_read: int
    theme_id: Optional[int]
    theme: Optional[ThemeOut]
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
    theme_id: Optional[int]
    theme: Optional[ThemeOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryUpdate(BaseModel):
    theme_id: Optional[int] = None
    tags: Optional[list[str]] = None


# ── Search ───────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    items: list[SummaryListItem]
    total: int
