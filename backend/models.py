from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    color = Column(String(7), default="#6366f1")  # hex color
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
    key_points = Column(JSON, default=list)   # list[str]
    sections = Column(JSON, default=list)     # list[{title, content}]
    tags = Column(JSON, default=list)         # list[str]
    duration_read = Column(Integer, default=5)  # minutes

    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=True)
    theme = relationship("Theme", back_populates="summaries")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
