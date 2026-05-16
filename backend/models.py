from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    system_prompt = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    summaries = relationship("Summary", back_populates="prompt", lazy="select")


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    color = Column(String(7), default="#6366f1")
    icon = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    summaries = relationship("Summary", back_populates="theme", lazy="select")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    youtube_url = Column(String(500), nullable=False)
    youtube_id = Column(String(20), nullable=False)
    language = Column(String(10), default="fr")

    transcript = Column(Text, nullable=True)
    summary_short = Column(Text, nullable=False)
    summary_long = Column(Text, nullable=False)
    key_points = Column(JSON, default=list)
    sections = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    duration_read = Column(Integer, default=5)

    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    feedback = Column(Integer, nullable=True)  # 1 = like, -1 = dislike, NULL = neutre

    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=True)
    theme = relationship("Theme", back_populates="summaries")

    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=True)
    prompt = relationship("Prompt", back_populates="summaries")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
